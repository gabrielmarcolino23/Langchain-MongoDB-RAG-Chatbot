import os
import streamlit as st
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import MongoDBAtlasVectorSearch
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from pymongo import MongoClient
from config.config import OPENAI_API_KEY, MONGODB_URI, MONGODB_DB, MONGODB_COLLECTION
from dotenv import load_dotenv

load_dotenv()

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
Você é um assistente virtual especializado em ajudar usuários com dúvidas na plataforma Zoppy. Sempre que possível, baseie suas respostas nas informações presentes no documento fornecido para garantir que as respostas sejam precisas e atualizadas.
Lembre-se seja sempre direto e objetivo em suas respostas, fornecendo instruções claras e concisas para ajudar o usuário a resolver seu problema.

### Estrutura da resposta:
1. **Consulta ao Documento**: Sempre que possível, busque a resposta no documento fornecido. Se a informação não estiver no documento, dê a melhor resposta possível com base no seu conhecimento.
2. **Esclarecimento e Instruções**: Forneça as instruções de forma clara e organizada. Inclua os passos a partir da home page da Zoppy, e informe pré-requisitos, se houver.
3. **Encerramento**: Finalize encorajando o usuário a continuar perguntando, caso precise de mais ajuda. Exemplo: "Se precisar de mais alguma coisa, estou à disposição!"

### Exceção:
- **Integração com Shopify**: Caso a pergunta seja sobre integração com Shopify, não forneça explicações detalhadas. Apenas direcione o usuário para o link oficial: [Zoppy-Shopify Integration](https://zoppy-vvb7.help.userguiding.com/pt/articles/1360-shopify).

Contexto:
{context}

Pergunta:
{question}

Resposta:
"""
)

def main():
    st.set_page_config(page_title="💬 Chatbot-oppem", page_icon="🍆")

    st.title("💬 Mike-Gpt")
    st.caption("🚀 Pergunte para nossa IA especialista em Zoppy")

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "Olá! Como posso ajudar você hoje?"}]
    
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("Você:")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        try:
            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        except ImportError as e:
            st.error(f"Erro ao importar OpenAIEmbeddings: {e}")
            st.stop()

        # Configurar a conexão com o MongoDB
        try:
            client = MongoClient(MONGODB_URI)
            db = client[MONGODB_DB]
            collection = db[MONGODB_COLLECTION]
            vetorstore = MongoDBAtlasVectorSearch(collection, embedding_function=embeddings)
        except Exception as e:
            st.error(f"Erro ao conectar ao MongoDB: {e}")
            st.stop()

        if "memory" not in st.session_state:
            st.session_state.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        try:
            qa = ConversationalRetrievalChain.from_llm(
                llm=ChatOpenAI(
                    openai_api_key=OPENAI_API_KEY,
                    temperature=0,
                    model_name="gpt-4o-mini",
                    max_tokens=500,
                ),
                retriever=vetorstore.as_retriever(search_kwargs={"k": 1}),
                memory=st.session_state.memory,
                chain_type="stuff",
                combine_docs_chain_kwargs={
                    "prompt": prompt_template
                },
                verbose=True
            )
        except Exception as e:
            st.error(f"Erro ao configurar ConversationalRetrievalChain: {e}")
            st.stop()

        try:
            resposta = qa({"question": user_input})
        except Exception as e:
            st.error(f"Erro ao obter a resposta do LLM: {e}")
            st.stop()

        st.session_state.messages.append({"role": "assistant", "content": resposta['answer']})
        st.chat_message("assistant").write(resposta['answer'])

if __name__ == "__main__":
    main()