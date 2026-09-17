# LTS Perez – Lap Time Simulator (Copa Truck)

Simulador de tempo de volta quasi-estático (QSS) calibrado especificamente para caminhões de corrida da Copa Truck. O projeto serve de base para a pesquisa de pós-graduação do engenheiro Perez em parceria técnica com a SARU Dynamics, derivado conceitualmente da linhagem educacional do LTS HASE.

O foco desta versão é ser direto, leve e rodável em computadores Windows com o mínimo de configuração possível, sem dependência de Docker, WSL ou Anaconda.

---

## Requisitos de sistema

- Sistema operacional: Windows 10/11 (ou Linux / macOS)
- Python: versão 3.10, 3.11 ou 3.12 (64-bit)
- Navegador web: Google Chrome, Microsoft Edge, Firefox ou Brave
- Git (opcional, pode-se baixar diretamente o arquivo ZIP)

---

## Estrutura do projeto

```text
LTS_Perez_CopaTruck/
│
├── app.py                      # Ponto de entrada do simulador Streamlit
├── requirements.txt            # Lista enxuta de bibliotecas Python
├── Makefile                    # Automação para ambientes Unix / Git Bash
├── .gitignore                  # Arquivos ignorados pelo controle de versão
├── README.md                   # Manual de instalação e operação
│
├── data/
│   ├── vehicle_models.json     # Fichas técnicas calibradas de veículos
│   └── tracks/                 # Circuitos em formato HDF5 (Interlagos, Cascavel)
│
├── tracks/                     # Espelho dos arquivos HDF5 de traçado
│   ├── cascavel.hdf5
│   └── interlagos.hdf5
│
├── src/
│   ├── simulation/             # Solver QSS de tempo de volta e dinâmicas
│   │   ├── lap_time_solver.py  # Algoritmo de aceleração e frenagem em duas passagens
│   │   ├── run_bicycle_model.py# Execução direta do modelo de dois graus de liberdade
│   │   ├── simulation_modes.py # Configurações (Qualificação, Largada Parada, Volta Lançada)
│   │   └── config.py           # Reexportações de configuração
│   │
│   ├── vehicle/                # Parâmetros e montagem do caminhão de corrida
│   │   ├── parameters.py       # Classes de massa, geometria, pneus, motor e freio
│   │   ├── copa_truck_default.py# Preset padrão pré-calibrado do caminhão
│   │   ├── regulation_validator.py# Validação de conformidade com regulamento CBA
│   │   └── fleet/              # Gerenciamento de presets de frota
│   │
│   ├── tracks/                 # Processamento de linhas centrais e trajetórias
│   │   ├── circuit.py          # Leitor e estruturas de dados de pista
│   │   ├── hdf5.py             # Parser HDF5 de geometria do circuito
│   │   ├── curvature.py        # Cálculo vetorial de curvatura e raio
│   │   ├── classification.py   # Classificação de retas e severidade de curvas
│   │   └── racing_line.py      # Traçado de raio ótimo considerando largura do caminhão
│   │
│   ├── visualization/          # Interface gráfica Streamlit
│   │   ├── interface.py        # Roteador central das páginas
│   │   ├── theme.py            # Paleta de cores e tipografia de engenharia
│   │   └── components/         # Módulos visuais (Parâmetros, Pista, Simulação, Resultados)
│   │
│   ├── analysis/               # Relatórios e balanço dinâmico do veículo
│   │   ├── handling_balance.py # Gradiente de subesterço e sobresterço
│   │   ├── brake_lockup.py     # Análise de travamento e distribuição de frenagem
│   │   └── driver_report.py    # Avaliação de pilotagem e consistência
│   │
│   └── validation/             # Scripts de teste de tempos reais
│       └── validate_laptimes_copa_truck.py # Validação contra pole positions reais
│
└── tests/                      # Bateria de testes automatizados com pytest
```

---

## Guia de instalação no Windows

Siga os passos abaixo na ordem indicada para configurar o simulador em um computador Windows limpo.

### Passo 0: Verificar e instalar o Python

1. Abra o Terminal do Windows ou o Prompt de Comando (pressione a tecla `Windows`, digite `cmd` e aperte `Enter`).
2. Digite o comando abaixo para verificar se o Python já está instalado:
   ```cmd
   python --version
   ```
3. Se aparecer `Python 3.10.x`, `Python 3.11.x` ou `Python 3.12.x`, avance para o Passo 1.
4. Se o comando não for reconhecido, instale o Python por uma das opções:
   - **Opção A (Recomendada - Instalador oficial):** Acesse [python.org/downloads](https://www.python.org/downloads/), baixe a versão estável mais recente do instalador Windows 64-bit. Ao iniciar a instalação, **marque obrigatoriamente a caixa de seleção "Add python.exe to PATH"** na primeira tela antes de clicar em "Install Now".
   - **Opção B (Via Terminal winget):** Execute no terminal do Windows:
     ```cmd
     winget install Python.Python.3.12
     ```
   - Feche e reabra o terminal para aplicar a variável de ambiente PATH.

---

### Passo 1: Baixar o projeto

Você pode obter o código-fonte de duas maneiras:

- **Se você tem o Git instalado:**
  ```cmd
  git clone https://github.com/vitormtt/LTS_CopaTruck.git
  cd LTS_CopaTruck
  ```
- **Se você NÃO tem o Git instalado:**
  1. Acesse o repositório no GitHub: `https://github.com/vitormtt/LTS_CopaTruck`
  2. Clique no botão verde **Code** e depois em **Download ZIP**.
  3. Extraia a pasta baixada em um diretório de sua preferência (por exemplo, na Área de Trabalho ou em `C:\Projetos`).
  4. Abra a pasta extraída no terminal.

---

### Passo 2: Criar o ambiente virtual

O ambiente virtual isola as bibliotecas do simulador sem interferir em outros programas.

No terminal, dentro da pasta do projeto, execute:

```cmd
python -m venv .venv
```

Um diretório chamado `.venv` será criado na raiz do projeto.

---

### Passo 3: Ativar o ambiente virtual

A forma de ativação varia conforme o terminal que você está utilizando:

#### Se estiver usando PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

*Nota sobre o PowerShell:* se o Windows bloquear a execução de scripts com um erro de política de segurança, execute antes o seguinte comando na mesma janela:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

#### Se estiver usando Prompt de Comando (CMD):
```cmd
.venv\Scripts\activate.bat
```

Quando ativado, o prefixo `(.venv)` aparecerá no início da linha de comando.

---

### Passo 4: Instalar as dependências

Com o ambiente virtual ativado, atualize o gerenciador de pacotes e instale as bibliotecas necessárias:

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

Aguarde o download e instalação dos pacotes (NumPy, SciPy, Pandas, Matplotlib, Plotly, Streamlit, h5py e ReportLab).

---

### Passo 5: Executar o simulador

Para iniciar a interface visual no seu navegador padrão, execute:

```cmd
streamlit run app.py
```

O Streamlit iniciará o servidor local e abrirá automaticamente uma aba no seu navegador no endereço:
`http://localhost:8501`

Se não abrir automaticamente, basta copiar o endereço indicado no terminal e colar na barra de navegação do seu navegador.

---

## Uso do Makefile (Git Bash, Linux e macOS)

Para desenvolvedores em ambientes compatíveis com `make` (como Git Bash no Windows, terminais Linux ou macOS), o `Makefile` automatiza todas as tarefas:

- Criar ambiente virtual:
  ```bash
  make venv
  ```
- Instalar dependências:
  ```bash
  make install
  ```
- Executar o simulador:
  ```bash
  make run
  ```
- Rodar a suíte de testes automatizados:
  ```bash
  make test
  ```
- Limpar arquivos temporários e ambiente virtual:
  ```bash
  make clean
  ```

*Usuários no Prompt de Comando comum do Windows podem ignorar o Makefile e seguir os comandos manuais descritos nas seções anteriores.*

---

## Como utilizar a interface

A navegação ocorre pelo menu lateral esquerdo do Streamlit, estruturado nas seguintes etapas:

1. **Parameters (Parâmetros do Veículo):**
   - Escolha um modelo da frota ou ajuste peso, distribuição longitudinal de massa, arrasto aerodinâmico, altura do centro de gravidade, rigidez de barra estabilizadora e curvas de motor/câmbio.
   - Clique em **Save vehicle setup** para confirmar as alterações.
2. **Track (Pista):**
   - Selecione o circuito desejado (Cascavel ou Interlagos).
   - Visualize a linha central e o traçado otimizado com a largura do caminhão.
   - Ajuste o multiplicador de aderência do asfalto caso queira simular condições de baixa ou alta borracha.
3. **Simulation (Configuração de Simulação):**
   - Selecione o modo de simulação (Qualificação com volta lançada periódica, Largada Parada ou Volta Rápida).
4. **Executar Simulação:**
   - No menu lateral, clique no botão azul **Run simulation**.
   - O solver quasi-estático (QSS) processará os limites de aceleração longitudinal e aceleração lateral ao longo de todo o circuito.
5. **Results (Resultados e Telemetria):**
   - Analise o tempo de volta consolidado, velocidade máxima e média, consumo de combustível e temperatura estimada de pneus.
   - Visualize gráficos sincronizados de velocidade, acelerações G (longitudinal e lateral), marcha engatada e traçado no mapa.
   - Exporte a telemetria em formato CSV ou gere o relatório completo em PDF.

---

## Validação contra tempos reais da Copa Truck

O projeto inclui um script autônomo para comparar os tempos de qualificação gerados pelo solver com as referências reais das pole positions oficiais da Copa Truck:

```cmd
python src/validation/validate_laptimes_copa_truck.py
```

### Referências técnicas adotadas:
- **Autódromo Zilmar Beux (Cascavel):**
  - Tempo real da pole position (Categoria Pro): 1:19.505 (79.505 s)
  - Velocidade máxima real no final da reta: ~193 km/h
- **Autódromo de Interlagos (São Paulo):**
  - Tempo real da pole position (Categoria Pro): 2:03.900 (123.900 s)
  - Limitador regulamentar: 200 km/h fixo

O modelo físico incorpora o regulamento desportivo e técnico da Confederação Brasileira de Automobilismo (CBA), respeitando o peso mínimo de 4.500 kg para a categoria e a curva de potência equalizada por restritor eletrônico.

---

## Solução de problemas comuns (Troubleshooting)

### 1. `python` não é reconhecido como um comando interno ou externo
- O Python foi instalado sem marcar a opção de adicionar ao PATH.
- Solução: reinstale o Python pelo instalador oficial e certifique-se de marcar a caixa **Add python.exe to PATH**, ou adicione manualmente o diretório de instalação do Python às Variáveis de Ambiente do Windows.

### 2. Erro de política de execução no PowerShell (`Execution_Policies`)
- O Windows impede a execução de scripts `.ps1` por padrão no PowerShell.
- Solução: execute o comando abaixo antes de ativar a venv:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 3. `ModuleNotFoundError: No module named 'src'`
- O Python não está encontrando a pasta do projeto.
- Solução: certifique-se de executar sempre `streamlit run app.py` ou `python src/...` a partir da **pasta raiz** do projeto (`LTS_CopaTruck`).

### 4. A porta 8501 do Streamlit já está em uso
- Se já houver outra instância do Streamlit aberta na mesma máquina, execute em outra porta:
  ```cmd
  streamlit run app.py --server.port 8502
  ```

---

## Licença e créditos

Desenvolvido no âmbito da pós-graduação de Engenharia Automotiva por Perez em colaboração com a SARU Dynamics. Baseado na arquitetura conceitual aberta do LTS HASE.
