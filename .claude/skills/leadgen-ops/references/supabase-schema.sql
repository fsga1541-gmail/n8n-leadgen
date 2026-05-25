-- Schema the n8n LangChain Supabase Vector Store node expects.
-- Run this once in Supabase → SQL Editor → New query.

-- pgvector extension
create extension if not exists vector;

-- Documents table — vector(1536) matches OpenAI text-embedding-3-small/large
create table if not exists documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- IVFFlat index for fast cosine similarity. lists=100 is fine up to ~1M rows.
create index if not exists documents_embedding_idx
  on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- The RPC that LangChain's SupabaseVectorStore calls under the hood.
-- The function name and signature must match exactly.
create or replace function match_documents (
  query_embedding vector(1536),
  match_count int default 5,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
