import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import aiofiles

from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.services.zilliz_service import zilliz_service
from app.tools.parsers.markdown_parser import MarkdownParser
from app.tools.parsers.text_processor import TextProcessor

# Configuration
DATASET_PATH = Path(__file__).parent.parent / "dataset" / "DRAGONBALL_docs.jsonl"
CONTEXTUALIZED_CACHE_PATH = (
    Path(__file__).parent.parent / "dataset" / "DRAGONBALL_docs_contextualized.jsonl"
)
COLLECTION_NAME = "dragonball_evaluation_contextualized"
CHUNK_SIZE = 500  # tokens
CHUNK_OVERLAP = 50  # tokens
USE_CACHE = True  # Set to False to force regenerate contextualized chunks

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Setup services
embed_model = embedding_service.embed_model
llm = llm_service.get_default_llm()

zilliz_service.collection_name = COLLECTION_NAME
zilliz_service.create_collection()


def extract_abstract_from_content(content: str) -> str:
    """Extract abstract from markdown content."""

    lines = content.split("\n")

    # Extract abstract (section after ## Abstract)
    in_abstract = False
    abstract_lines = []
    for line in lines:
        if line.startswith("## Abstract"):
            in_abstract = True
            continue
        if in_abstract:
            if line.startswith("##"):  # Next section
                break
            abstract_lines.append(line)

    if abstract_lines:
        return "\n".join(abstract_lines).strip()
    return ""


async def contextualize_chunk(
    chunk_text: str, context: str, use_full_paper: bool = False
) -> str:
    """Generate contextualized chunk using LLM.

    Args:
        chunk_text: The original chunk content
        context: Full paper content or section content
        use_full_paper: If True, context is full paper; if False, context is section

    Returns:
        Contextualized chunk with added context
    """
    context_type = "whole document" if use_full_paper else "section"

    prompt = f"""<document>

{context}

</document>

Here is the chunk we want to situate within the {context_type}

<chunk>

{chunk_text}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

    try:
        response = await llm.acomplete(prompt)
        context_snippet = str(response).strip()

        # Combine context snippet with original chunk
        contextualized_chunk = f"{context_snippet} {chunk_text}"
        return contextualized_chunk
    except Exception as e:
        logger.warning(f"Failed to contextualize chunk, using original: {e}")
        # Fallback to original chunk if LLM fails
        return chunk_text


# def chunk_content(content: str, chunk_size: int, overlap: int) -> list[dict]:
#     """Chunk content using TextProcessor with overlap."""

#     parser = MarkdownParser(min_content_length=50)
#     processor = TextProcessor(max_chunk_words=chunk_size)

#     # Parse into sections
#     sections = parser.parse_markdown_sections(content)

#     # Chunk each section
#     all_chunks = []

#     for section_idx, (section_name, section_content) in enumerate(sections.items()):
#         chunks = processor.split_into_chunks(
#             section_content, max_chunk_words=chunk_size, overlap_words=overlap
#         )

#         for chunk_idx, chunk_text in enumerate(chunks):
#             all_chunks.append(
#                 {
#                     "section_name": section_name,
#                     "section_index": section_idx,
#                     "chunk_index": chunk_idx,
#                     "content": chunk_text,
#                 }
#             )

#     return all_chunks


async def chunk_content(
    content: str, chunk_size: int, overlap: int, use_full_paper_context: bool = False
) -> list[dict]:
    """Chunk content using TextProcessor with overlap and contextualization."""

    parser = MarkdownParser(min_content_length=50)
    processor = TextProcessor(max_chunk_words=chunk_size)

    # Parse into sections
    sections = parser.parse_markdown_sections(content)

    # Chunk each section
    all_chunks = []

    for section_idx, (section_name, section_content) in enumerate(sections.items()):
        chunks = processor.split_into_chunks(
            section_content, max_chunk_words=chunk_size, overlap_words=overlap
        )

        for chunk_idx, chunk_text in enumerate(chunks):
            # Determine context to use
            if use_full_paper_context:
                context = content
            else:
                context = section_content
            # Contextualize the chunk
            contextualized_content = await contextualize_chunk(
                chunk_text=chunk_text,
                context=context,
                use_full_paper=use_full_paper_context,
            )

            all_chunks.append(
                {
                    "section_name": section_name,
                    "section_index": section_idx,
                    "chunk_index": chunk_idx,
                    "content": contextualized_content,
                }
            )

    return all_chunks


async def save_contextualized_chunks(
    doc_id: str, metadata: dict, chunks: list[dict]
) -> None:
    """Save contextualized chunks to cache file."""
    cache_data = {
        "doc_id": doc_id,
        "metadata": metadata,
        "chunks": chunks,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }

    try:
        async with aiofiles.open(CONTEXTUALIZED_CACHE_PATH, "a", encoding="utf-8") as f:
            await f.write(json.dumps(cache_data, ensure_ascii=False) + "\n")
        logger.debug(f"  Saved contextualized chunks to cache for doc_id={doc_id}")
    except Exception as e:
        logger.warning(f"  Failed to save cache for doc_id={doc_id}: {e}")


def load_contextualized_chunks_cache() -> dict[str, dict]:
    """Load contextualized chunks from cache file.

    Returns:
        Dictionary mapping doc_id to cached data {metadata, chunks}
    """
    cache = {}

    if not CONTEXTUALIZED_CACHE_PATH.exists():
        return cache

    try:
        with open(CONTEXTUALIZED_CACHE_PATH, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                doc_id = data["doc_id"]
                cache[doc_id] = {
                    "metadata": data["metadata"],
                    "chunks": data["chunks"],
                }
        logger.info(f"Loaded {len(cache)} documents from contextualized cache")
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")

    return cache


async def ingest_document(doc: dict, cached_chunks: dict | None = None) -> int:
    """Ingest single document into Zilliz.

    Args:
        doc: Document data from JSONL
        cached_chunks: Dictionary of cached contextualized chunks (doc_id -> {metadata, chunks})
    """

    content = doc["content"]
    metadata = doc["metadata"]
    doc_id = doc["doc_id"]

    # Normalize & prepare metadata
    paper_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"dragonball_doc_{doc_id}"))

    abstract = extract_abstract_from_content(content)

    year = metadata.get("year")
    if isinstance(year, str):
        try:
            year = int(year)
        except ValueError:
            year = 0

    logger.info(f"Processing: {metadata['title']}")
    logger.info(f"  Paper ID: {paper_id}")
    logger.info(f"  Authors: {', '.join(metadata['authors'])}")
    logger.info(f"  Venue: {metadata['venue']}, Year: {year}")
    logger.info(f"  Abstract length: {len(abstract)} characters")

    # Check cache first
    chunks = None
    if USE_CACHE and cached_chunks and doc_id in cached_chunks:
        logger.info(f"  ✅ Using cached contextualized chunks for doc_id={doc_id}")
        chunks = cached_chunks[doc_id]["chunks"]
    else:
        # Chunk content with contextualization
        logger.info(f"  Generating contextualized chunks for doc_id={doc_id}...")
        chunks = await chunk_content(
            content, CHUNK_SIZE, CHUNK_OVERLAP, use_full_paper_context=True
        )
        logger.info(f"  Generated {len(chunks)} contextualized chunks")

        # Save to cache
        if USE_CACHE:
            await save_contextualized_chunks(doc_id, metadata, chunks)

    # Prepare texts for embedding
    texts_to_embed = [
        metadata["title"],
        abstract,
        *[chunk["content"] for chunk in chunks],
    ]

    logger.info("  Generating embeddings...")
    embeddings = await embed_model.aget_text_embedding_batch(texts_to_embed)

    paper_title_embedding = embeddings[0]
    abstract_embedding = embeddings[1]
    chunk_embeddings = embeddings[2:]

    # Prepare data for insertion
    vectors = []
    for chunk, chunk_embedding in zip(chunks, chunk_embeddings, strict=False):
        chunk_id = f"{paper_id}_s{chunk['section_index']}_c{chunk['chunk_index']}"

        vectors.append(
            {
                "chunk_id": chunk_id,
                "paper_id": paper_id,
                "paper_title": metadata["title"],
                "authors": metadata["authors"],
                "venue": metadata["venue"],
                "year": year,
                "section_name": chunk["section_name"],
                "section_index": chunk["section_index"],
                "chunk_index": chunk["chunk_index"],
                "chunk_content": chunk["content"],
                "chunk_content_embedding": chunk_embedding,
                "paper_title_embedding": paper_title_embedding,
                "abstract_embedding": abstract_embedding,
                "collection_names": [],
                "chunk_references": [],
                "image_path": "",
                # BM25 will be generated by Zilliz analyzer from chunk_content
            }
        )

    # Insert into Zilliz
    logger.info(f"  Inserting {len(vectors)} vectors into Zilliz...")
    try:
        zilliz_service.client.insert(
            collection_name=zilliz_service.collection_name,
            data=vectors,
        )
        logger.info(f" Successfully inserted {len(vectors)} chunks")
    except Exception as e:
        logger.error(f" Failed to insert into Zilliz: {e}")
        raise

    return len(chunks)


async def main():
    """Main ingestion workflow."""
    logger.info("=" * 60)
    logger.info("Dataset Ingestion to Zilliz")
    logger.info("=" * 60)
    logger.info(f"Dataset: {DATASET_PATH}")
    logger.info(f"Collection: {COLLECTION_NAME}")
    logger.info(f"Chunk size: {CHUNK_SIZE} tokens")
    logger.info(f"Chunk overlap: {CHUNK_OVERLAP} tokens")
    logger.info(f"Use cache: {USE_CACHE}")
    logger.info(f"Cache file: {CONTEXTUALIZED_CACHE_PATH}")
    logger.info("=" * 60)

    if not DATASET_PATH.exists():
        logger.error(f"Dataset file not found: {DATASET_PATH}")
        return

    # Load cached contextualized chunks if available
    cached_chunks = None
    if USE_CACHE:
        cached_chunks = load_contextualized_chunks_cache()
        if cached_chunks:
            logger.info(f"Loaded {len(cached_chunks)} documents from cache")

    # Initialize Zilliz connection
    logger.info("Connecting to Zilliz...")
    try:
        zilliz_service.connect()
        logger.info(f"Connected to Zilliz collection: {zilliz_service.collection_name}")
    except Exception as e:
        logger.error(f"Failed to connect to Zilliz: {e}")
        return

    # Load and process JSONL
    total_chunks = 0
    doc_count = 0

    async with aiofiles.open(DATASET_PATH) as f:
        line_num = 0
        async for line in f:
            if not line.strip():
                continue

            line_num += 1
            doc = json.loads(line)
            logger.info(f"\n[Document {line_num}] doc_id={doc['doc_id']}")

            chunk_count = await ingest_document(doc, cached_chunks)
            total_chunks += chunk_count
            doc_count += 1

    logger.info("=" * 60)
    logger.info(
        f"✅ Successfully ingested {doc_count} documents, {total_chunks} total chunks"
    )
    logger.info(f"Contextualized chunks cache: {CONTEXTUALIZED_CACHE_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
