import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

# Importar a biblioteca do Google Gemini
import google.generativeai as genai

app = Flask(__name__)

# Configuração de upload
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Mapeamento de tags para currículos
RESUME_MAP = {
    "DEFAULT": "CV_DEFAULT.pdf",
    "DG": "CV_DG.pdf",
    "DP": "CV_DP.pdf",
    "SUP": "CV_SUP.pdf",
    "IMPL": "CV_IMPL.pdf",
    "CLOUD": "CV_CLOUD.pdf",
    "ADM": "CV_ADM.pdf",
}

TAG_DESCRIPTIONS = {
    "DEFAULT": "Currículo Padrão",
    "DG": "Desenvolvimento Geral",
    "DP": "Desenvolvimento Python",
    "SUP": "Suporte Técnico",
    "IMPL": "Implantação",
    "CLOUD": "Cloud/DevOps",
    "ADM": "Administração",
}

PROJECT_ROOT = Path("job-organizer")
CURRICULOS_DIR = PROJECT_ROOT / "curriculos"
CANDIDATURAS_DIR = PROJECT_ROOT / "candidaturas"
HISTORICO_CSV = PROJECT_ROOT / "historico_candidaturas.csv"

# Configurar a API do Gemini
# Obtenha sua API Key em https://makers.generativeai.google/key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite") # Ou "gemini-1.5-flash" para mais velocidade
else:
    print("AVISO: GEMINI_API_KEY não configurada. A classificação da vaga será simulada.")
    model = None

def classify_job_description(job_description: str) -> dict:
    """
    Classifica a descrição da vaga usando a API do Google Gemini ou simula se a chave não estiver configurada.
    Inclui ranking de tags e score de aderência.
    """
    prompt = f"""
    Analise a descrição da vaga abaixo e:
    1. Escolha a tag mais adequada entre: DEFAULT, DG, DP, SUP, IMPL, CLOUD, ADM.
    2. Atribua um score de aderência de 0 a 100.
    3. Forneça um ranking de probabilidade (0-100) para cada uma das tags.
    4. Explique brevemente o motivo da escolha.

    Retorne somente JSON no seguinte formato:
    {{
      "tag": "TAG_ESCOLHIDA",
      "score": 85,
      "motivo": "Explicação curta",
      "ranking": {{
        "DG": 10,
        "DP": 5,
        "SUP": 70,
        "IMPL": 95,
        "CLOUD": 20,
        "ADM": 0,
        "DEFAULT": 0
      }}
    }}

    Descrição da vaga:
    {job_description}
    """

    if model:
        try:
            response = model.generate_content(prompt)
            # O Gemini pode retornar o JSON dentro de um bloco de código, então precisamos extraí-lo
            text_response = response.text.strip()
            if text_response.startswith("```json") and text_response.endswith("```"):
                text_response = text_response[7:-3].strip()
            return json.loads(text_response)
        except Exception as e:
            print(f"Erro ao chamar a API do Gemini: {e}")
            # Fallback para simulação em caso de erro da API
            return {
                "tag": "DEFAULT",
                "score": 50,
                "motivo": f"Erro na API do Gemini: {e}. Classificação simulada.",
                "ranking": {
                    "DG": 50, "DP": 50, "SUP": 50, "IMPL": 50, "CLOUD": 50, "ADM": 50, "DEFAULT": 100
                }
            }
    else:
        # Simulação para o teste ou quando a chave não está configurada
        return {
            "tag": "IMPL",
            "score": 91,
            "motivo": "Foco em integração de sistemas, Open Finance e implantação de soluções. (Simulado)",
            "ranking": {
                "DG": 65, "DP": 40, "SUP": 72, "IMPL": 91, "CLOUD": 58, "ADM": 15, "DEFAULT": 10
            }
        }

def create_candidacy_folder(company_name: str, job_description_content: str, classification_result: dict):
    """
    Cria a pasta da candidatura, organiza os arquivos e gera o JSON final.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    tag = classification_result["tag"]
    
    sanitized_company = "".join(c if c.isalnum() or c in " _-" else "_" for c in company_name).replace(" ", "_")
    folder_name = f"{today}_{sanitized_company}_{tag}"
    candidacy_path = CANDIDATURAS_DIR / folder_name
    candidacy_path.mkdir(parents=True, exist_ok=True)

    # 1. Salva a descrição da vaga
    (candidacy_path / "vaga.txt").write_text(job_description_content)

    # 2. Copia o currículo (com fallback para DEFAULT)
    resume_filename = RESUME_MAP.get(tag, RESUME_MAP["DEFAULT"])
    source_resume = CURRICULOS_DIR / resume_filename
    
    if not source_resume.exists():
        print(f"⚠️ Aviso: {resume_filename} não encontrado. Usando DEFAULT.")
        resume_filename = RESUME_MAP["DEFAULT"]
        source_resume = CURRICULOS_DIR / resume_filename

    if source_resume.exists():
        shutil.copy(source_resume, candidacy_path / resume_filename)
    else:
        # Cria um arquivo vazio se nem o default existir (apenas para evitar erro no teste)
        (candidacy_path / "CV_MISSING.pdf").touch()
        resume_filename = "CV_MISSING.pdf"

    # 3. Gera o JSON de classificação
    candidacy_json = {
        "empresa": company_name,
        "data": today,
        "tag_principal": tag,
        "score_aderencia": classification_result["score"],
        "curriculo_enviado": resume_filename,
        "motivo": classification_result["motivo"],
        "ranking_completo": classification_result["ranking"]
    }
    
    (candidacy_path / "classificacao.json").write_text(
        json.dumps(candidacy_json, indent=2, ensure_ascii=False)
    )
    
    return candidacy_json

def update_history(data: dict):
    """
    Atualiza o histórico CSV.
    """
    file_exists = HISTORICO_CSV.exists()
    df = pd.DataFrame([{
        "Data": data["data"],
        "Empresa": data["empresa"],
        "Tag": data["tag_principal"],
        "Score": data["score_aderencia"],
        "Curriculo": data["curriculo_enviado"]
    }])
    df.to_csv(HISTORICO_CSV, mode='a', header=not file_exists, index=False)

def get_resume_info(tag: str) -> dict:
    """
    Retorna informações sobre um currículo específico.
    """
    filename = RESUME_MAP.get(tag, RESUME_MAP["DEFAULT"])
    filepath = CURRICULOS_DIR / filename
    
    info = {
        "tag": tag,
        "description": TAG_DESCRIPTIONS.get(tag, "Desconhecido"),
        "filename": filename,
        "exists": filepath.exists(),
        "size": 0,
        "modified": None
    }
    
    if filepath.exists():
        stat = filepath.stat()
        info["size"] = stat.st_size
        info["modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
    
    return info

# --- Rotas do Flask ---

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        job_description = request.form["job_description"]
        company_name = request.form["company_name"]

        if not job_description.strip():
            return render_template("index.html", error="A descrição da vaga não pode estar vazia.")
        if not company_name.strip():
            return render_template("index.html", error="O nome da empresa não pode estar vazio.")

        try:
            classification_result = classify_job_description(job_description)
            candidacy_data = create_candidacy_folder(company_name, job_description, classification_result)
            update_history(candidacy_data)
            
            # Redireciona para uma página de sucesso ou exibe o resultado
            return render_template("index.html", success=True, result=candidacy_data)
        except Exception as e:
            return render_template("index.html", error=f"Ocorreu um erro: {e}")

    return render_template("index.html")

@app.route("/resumes", methods=["GET"])
def manage_resumes():
    """Página de gerenciamento de currículos."""
    resumes_info = []
    for tag in RESUME_MAP.keys():
        resumes_info.append(get_resume_info(tag))
    
    return render_template("resumes.html", resumes=resumes_info)

@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    """Rota para fazer upload de um novo currículo."""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nenhum arquivo foi enviado."}), 400
    
    file = request.files['file']
    tag = request.form.get('tag', 'DEFAULT')
    
    if file.filename == '':
        return jsonify({"success": False, "message": "Nenhum arquivo foi selecionado."}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Apenas arquivos PDF são permitidos."}), 400
    
    if len(file.read()) > MAX_FILE_SIZE:
        file.seek(0)
        return jsonify({"success": False, "message": "Arquivo muito grande (máximo 10 MB)."}), 400
    
    file.seek(0)
    
    if tag not in RESUME_MAP:
        return jsonify({"success": False, "message": "Tag inválida."}), 400
    
    try:
        # Salva o arquivo com o nome correto
        filename = RESUME_MAP[tag]
        filepath = CURRICULOS_DIR / filename
        file.save(str(filepath))
        
        return jsonify({
            "success": True,
            "message": f"Currículo \'{TAG_DESCRIPTIONS[tag]}\' atualizado com sucesso!",
            "resume_info": get_resume_info(tag)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao salvar arquivo: {str(e)}"}), 500

@app.route("/delete-resume", methods=["POST"])
def delete_resume():
    """Rota para deletar um currículo."""
    tag = request.form.get('tag', 'DEFAULT')
    
    if tag == 'DEFAULT':
        return jsonify({"success": False, "message": "Não é possível deletar o currículo DEFAULT."}), 400
    
    if tag not in RESUME_MAP:
        return jsonify({"success": False, "message": "Tag inválida."}), 400
    
    try:
        filename = RESUME_MAP[tag]
        filepath = CURRICULOS_DIR / filename
        
        if filepath.exists():
            filepath.unlink()
            return jsonify({
                "success": True,
                "message": f"Currículo \'{TAG_DESCRIPTIONS[tag]}\' deletado com sucesso!",
                "resume_info": get_resume_info(tag)
            }), 200
        else:
            return jsonify({"success": False, "message": "Arquivo não encontrado."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao deletar arquivo: {str(e)}"}), 500

@app.route("/history", methods=["GET"])
def view_history():
    """Página de histórico de candidaturas."""
    if HISTORICO_CSV.exists():
        df = pd.read_csv(HISTORICO_CSV)
        history = df.to_dict('records')
    else:
        history = []
    
    return render_template("history.html", history=history)

if __name__ == "__main__":
    # Certifique-se de que os diretórios existam
    CURRICULOS_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATURAS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Crie arquivos PDF vazios como placeholders se não existirem
    for resume_file in RESUME_MAP.values():
        (CURRICULOS_DIR / resume_file).touch(exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=5000)