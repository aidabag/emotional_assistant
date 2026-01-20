import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Tuple
import tiktoken

# Инициализация ChromaDB
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../../data/chroma_db")
os.makedirs(CHROMA_PATH, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))


def get_collection():
    """Получить или создать коллекцию для документов"""
    return client.get_or_create_collection(
        name="reflection_documents",
        metadata={"description": "Документы для ассистента по эмоциональной саморефлексии"}
    )


def get_tokenizer():
    """Получить токенизатор для подсчета токенов"""
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except:
        return tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> List[str]:
    """Разбить текст на части с перекрытием"""
    tokenizer = get_tokenizer()
    tokens = tokenizer.encode(text)
    
    parts = []
    start = 0
    
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        part_tokens = tokens[start:end]
        part_text = tokenizer.decode(part_tokens)
        parts.append(part_text)
        
        if end >= len(tokens):
            break
        # Смещение для следующей части с перекрытием
        start = end - overlap
    
    return parts


def ingest_files(file_paths: List[str] = None) -> int:
    """
    Индексация файлов в векторное хранилище.
    Если file_paths не указаны, индексируются все .md и .txt файлы из директории data/.
    """
    if file_paths is None:
        data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        file_paths = []
        for ext in ["*.md", "*.txt"]:
            import glob
            file_paths.extend(glob.glob(os.path.join(data_dir, ext)))
            # Исключаем папку chroma_db и базу данных db.sqlite
            file_paths = [f for f in file_paths if "chroma_db" not in f and "db.sqlite" not in f]
    
    indexed_count = 0
    
    # Очистка существующей коллекции
    try:
        client.delete_collection("reflection_documents")
    except:
        pass
    
    collection = get_collection()
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue
        
        # Чтение содержимого файла
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Разбиение текста на части
        parts = chunk_text(content)
        
        # Подготовка данных для добавления в коллекцию
        ids = []
        documents = []
        metadatas = []
        
        for i, part in enumerate(parts):
            part_id = f"{os.path.basename(file_path)}_part_{i}"
            ids.append(part_id)
            documents.append(part)
            metadatas.append({
                "source": os.path.basename(file_path),
                "file_path": file_path,
                "part_index": i
            })
        
        # Добавление частей в коллекцию
        if ids:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            indexed_count += len(parts)
    
    return indexed_count


def search_rag(query: str, top_k: int = 3) -> List[Dict]:
    """Поиск релевантных частей текста в векторном хранилище"""
    try:
        collection = get_collection()
        collection_count = collection.count()
        if collection_count == 0:
            return []
        
        # Выполнение запроса к коллекции
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection_count)
        )
        
        parts = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                part = {
                    "content": doc,
                    "source": results["metadatas"][0][i].get("source", "unknown"),
                    "part_index": results["metadatas"][0][i].get("chunk_index", 0),
                    "distance": results["distances"][0][i] if results.get("distances") else None
                }
                parts.append(part)
        
        return parts
    except Exception as e:
        print(f"Ошибка при поиске RAG: {e}")
        return []
