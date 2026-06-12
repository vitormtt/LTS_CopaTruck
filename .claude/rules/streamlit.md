# Rules — Streamlit

<!-- Ativa neste repositório: LapTimeSimulator_CopaTruck usa Streamlit como interface principal -->

Padrões para apps Streamlit. Python 3.11+.

## Cache

- `@st.cache_data` obrigatório em funções de carregamento de dados (CSV, HDF5, JSON, API calls).
- `@st.cache_resource` para modelos pesados, conexões DB, objetos caros.
- Nunca usar `@st.experimental_memo` ou `@st.experimental_singleton` (deprecated).
- `ttl` explícito quando dados podem mudar: `@st.cache_data(ttl=300)`.

## Estado da sessão

- Estado via `st.session_state` com chave explícita: `st.session_state["vehicle_params"]`.
- Nunca usar variáveis globais mutáveis para estado compartilhado.
- Inicializar chaves do `session_state` no início do script antes de usar.

## Layout

- `st.sidebar` para controles e filtros de input.
- `st.columns([ratio, ratio])` para layout side-by-side.
- `st.tabs(["tab1", "tab2"])` para seções separadas.
- `st.expander("label")` para conteúdo opcional/técnico.

## Separação de responsabilidades

- **Lógica de negócio em Python puro** (fora do Streamlit).
- **Streamlit apenas para apresentação e I/O** — nunca calcular física dentro de callbacks.
- Funções de cálculo importadas de módulos separados; testáveis independentemente.
- O solver (`TwoPassSolver`) nunca deve importar `streamlit`.

## Callbacks e forms

- `st.form` para inputs que não devem re-rodar o app a cada keystroke.
- `on_change` callbacks devem ser curtos e sem side-effects pesados.
- `st.button` com `key` único quando há múltiplos botões.

## Proibições Streamlit

- `time.sleep()` em callbacks (congela o thread do Streamlit).
- `st.write()` para debug em produção (use `logging`).
- `st.experimental_*` (deprecated).
- Variáveis globais mutáveis como estado.
- Lógica de simulação/cálculo física dentro de funções Streamlit.
