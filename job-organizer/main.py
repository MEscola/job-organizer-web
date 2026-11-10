import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import pandas as pd
import google.generativeai as genai

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

PROJECT_ROOT = Path("job-organizer")
CURRICULOS_DIR = PROJECT_ROOT / "curriculos"
CANDIDATURAS_DIR = PROJECT_ROOT / "candidaturas"
HISTORICO_CSV = PROJECT_ROOT / "historico_candidaturas.csv"

# Configurar a API do Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")
else:
    print("AVISO: GEMINI_API_KEY não configurada. A classificação da vaga será simulada.")
    model = None

def classify_job_description(job_description: str) -> dict:
    """
    Classifica a descrição da vaga usando a API do Google Gemini.
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
            text_response = response.text.strip()
            # Remover blocos de código se presentes
            if text_response.startswith("```json"):
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif text_response.startswith("```"):
                text_response = text_response.split("```")[1].split("```")[0].strip()
            
            return json.loads(text_response)
        except Exception as e:
            print(f"Erro ao chamar a API do Gemini: {e}")
            # Fallback para simulação
    
    # Simulação para quando a chave não está configurada ou ocorre erro
    print("\n--- Modo de Simulação Ativo ---")
    print(f"Processando vaga para classificação...")
    return {
        "tag": "IMPL",
        "score": 91,
        "motivo": "Foco em integração de sistemas e implantação de soluções (Simulado).",
        "ranking": {
            "DG": 65, "DP": 40, "SUP": 72, "IMPL": 91, "CLOUD": 58, "ADM": 15, "DEFAULT": 10
        }
    }

def create_candidacy_folder(company_name: str, job_description_content: str, classification_result: dict):
    """
    Cria a pasta da candidatura e organiza os arquivos.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    tag = classification_result["tag"]
    
    sanitized_company = "".join(c if c.isalnum() or c in " _-" else "_" for c in company_name).replace(" ", "_")
    folder_name = f"{today}_{sanitized_company}_{tag}"
    candidacy_path = CANDIDATURAS_DIR / folder_name
    candidacy_path.mkdir(parents=True, exist_ok=True)

    (candidacy_path / "vaga.txt").write_text(job_description_content)

    resume_filename = RESUME_MAP.get(tag, RESUME_MAP["DEFAULT"])
    source_resume = CURRICULOS_DIR / resume_filename
    
    if not source_resume.exists():
        resume_filename = RESUME_MAP["DEFAULT"]
        source_resume = CURRICULOS_DIR / resume_filename

    if source_resume.exists():
        shutil.copy(source_resume, candidacy_path / resume_filename)
    else:
        (candidacy_path / "CV_MISSING.pdf").touch()
        resume_filename = "CV_MISSING.pdf"

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
    """Atualiza o histórico CSV."""
    file_exists = HISTORICO_CSV.exists()
    df = pd.DataFrame([{
        "Data": data["data"],
        "Empresa": data["empresa"],
        "Tag": data["tag_principal"],
        "Score": data["score_aderencia"],
        "Curriculo": data["curriculo_enviado"]
    }])
    df.to_csv(HISTORICO_CSV, mode='a', header=not file_exists, index=False)

def main():
    print("="*30)
    print("🚀 JOB ORGANIZER PRO (GEMINI)")
    print("="*30)
    
    print("\n[1] Cole a descrição da vaga (Pressione Ctrl+D ou Enter 3x para processar):")
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if not line.strip():
                empty_count += 1
            else:
                empty_count = 0
            if empty_count >= 3:
                break
            lines.append(line)
        except EOFError:
            break
            
    job_text = "\n".join(lines).strip()
    if not job_text:
        print("❌ Descrição vazia.")
        return

    company = input("\n[2] Nome da Empresa: ").strip()
    if not company:
        company = "Empresa_Nao_Informada"

    result = classify_job_description(job_text)
    print(f"\n✅ Tag: {result['tag']} | Score: {result['score']}%")
    
    candidacy_data = create_candidacy_folder(company, job_text, result)
    update_history(candidacy_data)
    
    print(f"\n✨ Candidatura organizada com sucesso!")

if __name__ == "__main__":
    main()
