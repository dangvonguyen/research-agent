import asyncio
import time

from app.ai.tools.structure_extract import StructuredExtractorTool


async def main():
    tool = StructuredExtractorTool()

    paper_ids = [
        "18320fde-b6a3-4683-845d-7800a9091b4a",
        "b25c8e42-7550-4e61-a106-1c65a0d020a9",
    ]
    schema = {
        "dataset": {
            "name": "str",
            "source": "str",
            "languages": "list[str]",
            "statistics": {
                "words": "number",
                "definitions": "number",
                "synonyms": "number"
            },
            "evaluation_settings": "list[str]"
        },
        "evaluation_metrics": "list[str]",
        "main_results": {
            "summary": "str",
            "key_numbers": "list[str]"
        }
    }

    start = time.perf_counter()

    result = await tool.arun(
        paper_ids=paper_ids,
        extraction_schema=schema
    )

    end = time.perf_counter()

    print("=== Tool Output ===")
    print(result)
    print(f"\nExecution time: {end - start:.3f} seconds")


if __name__ == "__main__":
    asyncio.run(main())