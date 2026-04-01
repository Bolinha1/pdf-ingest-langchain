import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector

load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY")
_db_url = os.getenv("DATABASE_URL")

if not _api_key:
    raise EnvironmentError("OPENAI_API_KEY não definida no ambiente.")
if not _db_url:
    raise EnvironmentError("DATABASE_URL não definida no ambiente.")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=_api_key,
)

llm = ChatOpenAI(
    model="gpt-5-nano",
    api_key=_api_key,
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="pdf_documents",
    connection=_db_url,
)
