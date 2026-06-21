"""
Example Integration of Hardened NLP Components
==============================================

This file demonstrates how to integrate the deterministic ID generator
and provenance-aware mapper into the existing Mahoun pipeline.
This is for illustrative purposes - actual integration would modify
the relevant pipeline components.
"""

# Example showing how to integrate the new components into EnhancedIngestionPipeline

"""
ORIGINAL CODE (in enhanced_pipeline.py, around line 190-194):
                 # Re-extract with enhanced NER for cross-validation
                 enhanced_entities = self.ner_engine.extract(text)
                 # Merge results (prefer enhanced if more complete)
                 if len(enhanced_entities.get("persons", [])) > len(entities.get("persons", [])):
                     verdict_struct["entities"] = enhanced_entities
"""

"""
INTEGRATED VERSION WITH PROVENANCE MAPPING:
"""

# Add imports at top of file:
# from .deterministic_id_generator import DeterministicEntityIDGenerator
# from .provenance_aware_mapper import ProvenanceAwareNERMapper, ChunkInfo

# ─────────────────────────────────────────────────────────────────────────────
# ILLUSTRATIVE INTEGRATION SNIPPET
# (Not an executable class — shows how to modify EnhancedIngestionPipeline)
# ─────────────────────────────────────────────────────────────────────────────
#
# In enhanced_pipeline.py, update __init__ to add the hardened components:
#
#   def __init__(self, **kwargs):
#       # ... existing initialization ...
#       # NEW: Add hardened components
#       self.entity_id_generator = DeterministicEntityIDGenerator(
#           namespace="mahoun-legal-v1"
#       )
#       self.provenance_mapper = ProvenanceAwareNERMapper(
#           overlap_handling_strategy="assign_to_first"
#       )
#       # ... rest of existing init ...
#
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# ILLUSTRATIVE METHOD SNIPPETS
# These show how to extend EnhancedIngestionPipeline — not runnable as-is.
# ─────────────────────────────────────────────────────────────────────────────
#
# async def ingest_document(self, doc_id, text, metadata=None):
#     # ... existing code up to chunk creation ...
#
#     # STANDARD DOCUMENT PATH:
#     chunks = self.chunker.chunk_document(text=text, doc_id=doc_id, metadata=metadata)
#
#     # NEW: Register chunks with provenance mapper
#     self.provenance_mapper.register_chunks([
#         {
#             "chunk_id": chunk.chunk_id,
#             "doc_id": chunk.metadata.get("doc_id", doc_id),
#             "start": chunk.start,
#             "end": chunk.end,
#             "text": chunk.text,
#             "metadata": chunk.metadata,
#             "chunk_index": i,
#         }
#         for i, chunk in enumerate(chunks)
#     ])
#
#     # NEW APPROACH: Extract per-chunk, map to doc-relative coords:
#     all_entities = {"persons": [], "organizations": [], "courts": [],
#                     "laws": [], "topics": [], "legal_concepts": []}
#
#     for chunk in chunks:
#         chunk_entities = self.ner_engine.extract(chunk.text)
#         mapped = self._map_and_enrich_entities(chunk_entities, chunk, doc_id)
#         for etype in all_entities:
#             all_entities[etype].extend(mapped.get(etype, []))
#
#     entities = all_entities
#     # ... rest of existing pipeline continues ...
#
#
# def _map_and_enrich_entities(self, chunk_entities, chunk, doc_id):
#     """Map chunk-relative positions to doc-relative + attach provenance."""
#     document_entities = {"persons": [], "organizations": [], "courts": [],
#                          "laws": [], "topics": [], "legal_concepts": []}
#     chunk_start = chunk.start
#
#     for etype, ents in chunk_entities.items():
#         for entity in ents:
#             doc_entity = entity.copy()
#             if "start" in entity and "end" in entity:
#                 doc_entity["start"] = entity["start"] + chunk_start
#                 doc_entity["end"]   = entity["end"]   + chunk_start
#             doc_entity["_chunk_provenance"] = {
#                 "chunk_id":    chunk.chunk_id,
#                 "chunk_start": chunk.start,
#                 "chunk_end":   chunk.end,
#             }
#             document_entities[etype].append(doc_entity)
#
#     return self._apply_deterministic_ids_and_provenance(document_entities, doc_id)
#
#
# def _apply_deterministic_ids_and_provenance(self, entities, doc_id):
#     """Apply deterministic IDs + provenance via ProvenanceAwareNERMapper."""
#     mapped_entities = {}
#     for etype, elist in entities.items():
#         mapped_list = self.provenance_mapper.map_entities_to_chunks(elist, doc_id)
#         for entity in mapped_list:
#             entity_data = {"text": entity.get("text", ""), "entity_type": etype.upper()}
#             if etype == "persons":
#                 entity_data.update({k: entity.get(k) for k in
#                                     ("name", "father_name", "title", "national_id")})
#             elif etype == "organizations":
#                 entity_data.update({k: entity.get(k) for k in
#                                     ("name", "org_type", "registration_id")})
#             elif etype == "laws":
#                 entity_data.update({k: entity.get(k) for k in
#                                     ("article_number", "law_name")})
#
#             entity["entity_id"] = self.entity_id_generator.generate_entity_id(
#                 entity_type=etype.rstrip("s").lower(),
#                 entity_data=entity_data,
#                 context={"doc_id": doc_id},
#             )
#             prov = entity.get("provenance", {})
#             entity["provenance"] = {
#                 "chunk_id":             prov.get("chunk_id"),
#                 "chunk_relative_start": prov.get("chunk_relative_start"),
#                 "chunk_relative_end":   prov.get("chunk_relative_end"),
#                 "chunk_index":          prov.get("chunk_index"),
#                 "provenance_method":    prov.get("provenance_method"),
#                 "confidence_adjustment":prov.get("confidence_adjustment", 0.0),
#                 "warnings":             prov.get("warnings", []),
#             }
#         mapped_entities[etype] = mapped_list
#     return mapped_entities
