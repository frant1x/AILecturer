import hashlib
import os
import pickle
import uuid
from base64 import b64decode
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.schema.document import Document
from langchain.storage import InMemoryStore
from unstructured.partition.pdf import partition_pdf


ID_KEY = "doc_id"


def get_paths(course_id):
    """
    Generate file paths for storing vectorstore and docstore data for a specific course.
    """
    base = f"./courses_data/{course_id}"
    os.makedirs(base, exist_ok=True)
    vectorstore_dir = os.path.join(base, "chroma_db")
    docstore_path = os.path.join(base, "docstore.pkl")
    return vectorstore_dir, docstore_path


def get_file_hash(file):
    """Compute SHA256 hash of a file-like object."""
    sha256 = hashlib.sha256()
    for chunk in file.chunks():
        sha256.update(chunk)
    return sha256.hexdigest()


load_dotenv()


def pdf_partition(file_path):
    """
    Partition a PDF into texts, tables, and images using Unstructured library.
    """
    chunks = partition_pdf(
        filename=file_path,
        infer_table_structure=True,
        strategy="hi_res",
        extract_image_block_types=["Image"],
        extract_image_block_to_payload=True,
        chunking_strategy="by_title",
        max_characters=10000,
        combine_text_under_n_chars=2000,
        new_after_n_chars=6000,
    )

    tables = []
    texts = []

    for chunk in chunks:
        if "CompositeElement" in str(type(chunk)):
            for element in chunk.metadata.orig_elements:
                if "Table" in str(type(element)):
                    tables.append(element)
            texts.append(chunk)

    images = []
    for chunk in chunks:
        if "CompositeElement" in str(type(chunk)):
            for element in chunk.metadata.orig_elements:
                if "Image" in str(type(element)):
                    images.append(element.metadata.image_base64)

    return texts, tables, images


def summarize_all(texts, tables, images):
    """
    Generate summaries for extracted texts, tables, and images.
    """

    prompt_text = ChatPromptTemplate.from_template(
        """
    Ти — асистент, завдання якого полягає в детальному узагальненні таблиць та тексту.
    Надай стисле, але детальне узагальнення таблиці або тексту 
    
    Відповідай лише узагальненням, без жодних додаткових коментарів.
    Не починай повідомлення словами "Ось підсумок" чи подібними.
    Просто наведи узагальнення як є.
    
    Таблиця або текстовий фрагмент: {element}
    """
    )
    summarize_chain = (
        {"element": lambda x: x}
        | prompt_text
        | ChatOpenAI(temperature=0.5, model="gpt-4o-mini")
        | StrOutputParser()
    )

    text_summaries = summarize_chain.batch(texts, {"max_concurrency": 3})
    tables_html = [t.metadata.text_as_html for t in tables]
    table_summaries = summarize_chain.batch(tables_html, {"max_concurrency": 3})

    prompt_template = """Опиши зображення в деталях.  
    Будь конкретним щодо графіків, таких як стовпчикові діаграми."""

    image_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                [
                    {
                        "type": "text",
                        "text": prompt_template,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image}"},
                    },
                ],
            )
        ]
    )
    image_chain = image_prompt | ChatOpenAI(model="gpt-4o-mini") | StrOutputParser()
    image_summaries = image_chain.batch(images)

    return text_summaries, table_summaries, image_summaries


def get_retriever(course_id):
    """
    Initialize a MultiVectorRetriever with Chroma vectorstore and document store.
    """
    vectorstore_dir, docstore_path = get_paths(course_id)

    vectorstore = Chroma(
        collection_name="multi_modal_rag",
        embedding_function=OpenAIEmbeddings(),
        persist_directory=vectorstore_dir,
    )

    try:
        with open(docstore_path, "rb") as f:
            store = pickle.load(f)
    except FileNotFoundError:
        store = InMemoryStore()

    return MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=store,
        id_key=ID_KEY,
    )


def add_pdf(
    course_id,
    retriever,
    texts,
    text_summaries,
    tables,
    table_summaries,
    images,
    image_summaries,
):
    """
    Add summarized and original versions of texts, tables, and images to the retriever.
    """
    text_ids = [str(uuid.uuid4()) for _ in texts]
    summary_texts = [
        Document(page_content=summary, metadata={ID_KEY: text_ids[i]})
        for i, summary in enumerate(text_summaries)
    ]
    if summary_texts:
        retriever.vectorstore.add_documents(summary_texts)
        retriever.docstore.mset(list(zip(text_ids, texts)))

    table_ids = [str(uuid.uuid4()) for _ in tables]
    summary_tables = [
        Document(page_content=summary, metadata={ID_KEY: table_ids[i]})
        for i, summary in enumerate(table_summaries)
    ]
    if summary_tables:
        retriever.vectorstore.add_documents(summary_tables)
        retriever.docstore.mset(list(zip(table_ids, tables)))

    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(page_content=summary, metadata={ID_KEY: img_ids[i]})
        for i, summary in enumerate(image_summaries)
    ]
    if summary_img:
        retriever.vectorstore.add_documents(summary_img)
        retriever.docstore.mset(list(zip(img_ids, images)))

    _, docstore_path = get_paths(course_id)
    with open(docstore_path, "wb") as f:
        pickle.dump(retriever.docstore, f)

    all_ids = text_ids + table_ids + img_ids
    return all_ids


def remove_pdf(course_id, retriever, doc_ids):
    """
    Remove documents from vectorstore and docstore using their IDs.
    """
    if doc_ids:
        retriever.vectorstore.delete(ids=doc_ids)
        retriever.docstore.mdelete(doc_ids)

    _, docstore_path = get_paths(course_id)
    with open(docstore_path, "wb") as f:
        pickle.dump(retriever.docstore, f)


def parse_docs(docs):
    """Split base64-encoded images and texts"""
    b64 = []
    text = []
    for doc in docs:
        try:
            b64decode(doc)
            b64.append(doc)
        except Exception as e:
            text.append(doc)
    return {"images": b64, "texts": text}


def build_prompt(kwargs):
    """
    Construct a multimodal prompt for GPT using extracted text and image data.
    """
    docs_by_type = kwargs["context"]
    user_question = kwargs["question"]

    context_text = ""
    if len(docs_by_type["texts"]) > 0:
        for text_element in docs_by_type["texts"]:
            context_text += text_element.text

    prompt_template = f"""
    Дай відповідь на запитання, ґрунтуючись лише на наступному контексті, який може включати текст, таблиці та зображення нижче.
    Якщо у наданому контексті немає відповіді, то так і напиши.
    Контекст: {context_text}
    Запитання: {user_question}
    """

    prompt_content = [{"type": "text", "text": prompt_template}]

    if len(docs_by_type["images"]) > 0:
        for image in docs_by_type["images"]:
            prompt_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                }
            )

    return ChatPromptTemplate.from_messages(
        [
            HumanMessage(content=prompt_content),
        ]
    )
