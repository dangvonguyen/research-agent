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
        "dataset": "str",
        "evaluation_metric": "str",
        "main_results": "str",
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