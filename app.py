import streamlit as st

st.title("Gerador de Casos de Teste")
tarefa = st.text_area("Descrição da tarefa e critérios de aceite")
if st.button("Gerar"):
    st.write("Funcionando! Recebi:", tarefa)