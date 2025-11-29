import os
import glob
from typing import List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


class RAGService:
    """Service for Retrieval-Augmented Generation using FAISS vector store."""
    
    def __init__(self, data_dir: str = None, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize RAG service.
        
        Args:
            data_dir: Directory containing PDF files. Defaults to myapp/data
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        if data_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            data_dir = os.path.join(project_root, 'myapp', 'data')
        
        self.data_dir = data_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_store = None
        self.embeddings = None
        
    def load_documents(self) -> List[Document]:
        """
        Load all PDF documents from the data directory.
        
        Returns:
            List of Document objects
        """
        pdf_files = glob.glob(os.path.join(self.data_dir, "*.pdf"))
        
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in {self.data_dir}")
        
        print(f"Found {len(pdf_files)} PDF file(s): {[os.path.basename(f) for f in pdf_files]}")
        
        all_documents = []
        for pdf_file in pdf_files:
            try:
                loader = PyPDFLoader(pdf_file)
                documents = loader.load()
                print(f"Loaded {len(documents)} pages from {os.path.basename(pdf_file)}")
                all_documents.extend(documents)
            except Exception as e:
                print(f"Error loading {pdf_file}: {str(e)}")
                continue
        
        return all_documents
    
    def initialize_vector_store(self, force_rebuild: bool = False):
        """
        Initialize the FAISS vector store with document embeddings.
        
        Args:
            force_rebuild: If True, rebuild the vector store even if it exists
        """
        vector_store_path = os.path.join(self.data_dir, "faiss_index")
        
        # Try to load existing vector store
        if not force_rebuild and os.path.exists(vector_store_path):
            try:
                print("Loading existing FAISS index...")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                self.vector_store = FAISS.load_local(
                    vector_store_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print("FAISS index loaded successfully")
                return
            except Exception as e:
                print(f"Error loading existing index: {str(e)}. Rebuilding...")
        
        # Build new vector store
        print("Building new FAISS index...")
        
        # Load documents
        documents = self.load_documents()
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Split into {len(chunks)} chunks")
        
        # Create embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Create vector store
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        
        # Save vector store
        self.vector_store.save_local(vector_store_path)
        print(f"FAISS index saved to {vector_store_path}")
    
    def get_relevant_context(self, query: str, k: int = 4) -> Tuple[str, List[Document]]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User query
            k: Number of relevant chunks to retrieve
            
        Returns:
            Tuple of (concatenated context string, list of retrieved documents)
        """
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized. Call initialize_vector_store() first.")
        
        # Retrieve relevant documents
        retrieved_docs = self.vector_store.similarity_search(query, k=k)
        
        # Concatenate context
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        return context, retrieved_docs
    
    def get_relevant_context_with_scores(self, query: str, k: int = 4) -> Tuple[str, List[Tuple[Document, float]]]:
        """
        Retrieve relevant context with similarity scores.
        
        Args:
            query: User query
            k: Number of relevant chunks to retrieve
            
        Returns:
            Tuple of (concatenated context string, list of (document, score) tuples)
        """
        if self.vector_store is None:
            raise RuntimeError("Vector store not initialized. Call initialize_vector_store() first.")
        
        # Retrieve relevant documents with scores
        docs_with_scores = self.vector_store.similarity_search_with_score(query, k=k)
        
        # Concatenate context
        context = "\n\n".join([doc.page_content for doc, score in docs_with_scores])
        
        return context, docs_with_scores
