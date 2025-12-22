import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI, OpenAIError
from tqdm import tqdm

from .exceptions import APIError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Client class for generating text responses using a language model.

    Attributes:
        client: The client object used for API requests.
        model_name: The name of the model to use for generation.
    """

    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2  # Exponential backoff factor
    MIN_SLEEP_TIME = 0.5
    MAX_SLEEP_TIME = 2

    def __init__(self, openai_api_key: str, model_name: str):
        """
        Initializes the OpenAIClient instance with the given OpenAI API key and model name.

        Args:
            openai_key: The API key for the OpenAI service.
            model_name: The name of the model to use for generating responses.
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model_name = model_name

    def generate(
        self, input_list: list[dict], batch_size: int | None = None, **params
    ) -> list[str]:
        """
        Generates responses for a list of input prompts using the language model.

        Args:
            input_list: A list of input dictionaries containing "system_prompt" and "user_prompt".
            batch_size: The batch size for processing (optional).
            **params: Additional parameters for the API request.

        Returns:
            A list of generated responses corresponding to the input prompts.

        Raises:
            Exception: If some tasks fail to generate responses.
        """

        def process_task(idx: int, task_in: dict):
            """
            Processes a single task for generating a response.

            Args:
                idx: The index of the task.
                task_in: A dictionary containing the prompts for the task.

            Returns:
                A tuple of the task index and the generated response.
            """
            system_prompt = task_in["system_prompt"]
            user_prompt = task_in["user_prompt"]
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            retry_count = 0

            while retry_count < self.MAX_RETRIES:
                try:
                    time.sleep(random.uniform(self.MIN_SLEEP_TIME, self.MAX_SLEEP_TIME))
                    response = self.client.chat.completions.create(
                        messages=messages,
                        model=self.model_name,
                        # temperature=0,
                        top_p=1.0,
                        n=1,
                        stream=False,
                        frequency_penalty=0.0,
                        presence_penalty=0.0,
                        # logit_bias={},
                        **params,
                    ).model_dump()
                    response_text = response["choices"][0]["message"]["content"]
                    return idx, response_text

                except OpenAIError as e:
                    retry_count += 1
                    if retry_count >= self.MAX_RETRIES:
                        logger.error(
                            f"Task {idx} failed after {self.MAX_RETRIES} attempts: {e}"
                        )
                        return idx, None

                    # Exponential backoff: 1s, 2s, 4s, 8s, etc.
                    wait_time = min(self.BACKOFF_FACTOR**retry_count, 60)
                    logger.warning(
                        f"Task {idx} attempt {retry_count}/{self.MAX_RETRIES} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)

                except Exception as e:
                    # Unexpected errors should not be retried
                    logger.error(f"Task {idx} encountered unexpected error: {e}")
                    return idx, None

            # If max retries are reached, return None
            logger.error(f"Task {idx} failed after {self.MAX_RETRIES} attempts.")
            return idx, None

        responses = [None] * len(input_list)

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_task = {
                executor.submit(process_task, idx, task): task
                for idx, task in enumerate(input_list)
            }

            for future in tqdm(
                as_completed(future_to_task),
                total=len(input_list),
                desc="Generation process: ",
            ):
                try:
                    idx, response = future.result()
                    if response is not None:
                        responses[idx] = response
                except Exception as e:
                    logger.error(f"Error in future result retrieval: {e}")

        if None in responses:
            failed_indices = [i for i, r in enumerate(responses) if r is None]
            raise APIError(
                f"Failed to generate responses for {len(failed_indices)} tasks: {failed_indices}"
            )

        return responses
