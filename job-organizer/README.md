# Job Organizer Pro (Versão Gemini)

Este projeto Python automatiza o processo de organização de candidaturas a vagas de emprego, classificando descrições de vagas usando a API do **Google Gemini** e organizando os currículos e dados de candidatura em uma estrutura de pastas.

## Arquitetura

```
vaga.txt
    ↓
Python (Flask)
    ↓
Google Gemini API
    ↓
Classificação + Score + Ranking
    ↓
Escolha do currículo
    ↓
Criação da candidatura + Histórico CSV
```

## Funcionalidades

- **Classificação Automática**: Identifica a melhor categoria para a vaga (DG, DP, SUP, IMPL, CLOUD, ADM).
- **Score de Aderência**: Calcula quão bem seu currículo se encaixa na descrição da vaga.
- **Ranking de Tags**: Mostra a probabilidade de a vaga pertencer a outras categorias.
- **Gerenciamento de Currículos**: Interface web para fazer upload e gerenciar seus diferentes PDFs.
- **Histórico Completo**: Acompanhe todas as suas candidaturas e estatísticas em uma planilha CSV e interface web.

## Configuração

1.  **Instale as dependências:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Obtenha sua API Key do Gemini:**

    - Vá para o [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Crie uma nova API Key (é gratuito para uso pessoal dentro dos limites).

3.  **Configure a variável de ambiente:**

    No Linux/macOS:
    ```bash
    export GEMINI_API_KEY="sua_chave_aqui"
    ```

    No Windows (PowerShell):
    ```powershell
    $env:GEMINI_API_KEY="sua_chave_aqui"
    ```

## Como Usar

### Interface Web (Recomendado)

1.  Execute o servidor:
    ```bash
    python app.py
    ```
2.  Abra `http://localhost:5000` no seu navegador.
3.  Vá em **"Gerenciar Currículos"** e faça o upload dos seus PDFs para cada categoria.
4.  Na página inicial, cole a descrição da vaga e o nome da empresa para processar.

### Linha de Comando

1.  Execute o script:
    ```bash
    python main.py
    ```
2.  Siga as instruções no terminal para colar a vaga e informar a empresa.

## Estrutura de Pastas

```
job-organizer/
├── curriculos/          # Seus PDFs de currículo
├── candidaturas/        # Pastas organizadas por vaga
├── templates/           # Arquivos HTML da interface web
├── app.py               # Servidor Web Flask
├── main.py              # Script de linha de comando
└── historico_candidaturas.csv
```

## Licença

MIT
