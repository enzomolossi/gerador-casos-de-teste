import streamlit as st
from gerador import gerar_casos

st.title("Gerador de Casos de Teste")
tarefa = st.text_area("Descrição da tarefa e critérios de aceite", height=200)

if st.button("Gerar") and tarefa.strip():
    with st.spinner("Gerando..."):
        try:
            casos = gerar_casos(tarefa)
        except Exception as e:
            st.error(f"Erro: {e}")
        else:
            for c in casos:
                with st.expander(f"[{c['tipo']}] {c['titulo']}"):
                    st.caption(f"Critério: {c['criterio']}")
                    st.code(c["gherkin"], language="gherkin")