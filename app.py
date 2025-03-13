import os
import zipfile
import multiprocessing
from flask import Flask, request, render_template, send_file
from PyPDF2 import PdfReader, PdfWriter
from concurrent.futures import ProcessPoolExecutor

def extrair_arquivos(zip_path, extract_path):
    """Extrai os arquivos ZIP para um diretório especificado."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print(f"📂 Arquivos extraídos para: {extract_path}")
    print("📋 Conteúdo extraído:", os.listdir(extract_path))

def processar_holerite(pdf_path, nome_colaborador, output_dir):
    """Verifica se o PDF pertence ao colaborador e move para a pasta destino."""
    try:
        with open(pdf_path, "rb") as file:
            reader = PdfReader(file)
            paginas_encontradas = [(i, page) for i, page in enumerate(reader.pages) if page.extract_text() and nome_colaborador in page.extract_text()]
            
            if paginas_encontradas:
                escritor = PdfWriter()
                for i, (num_pagina, pagina) in enumerate(paginas_encontradas):
                    escritor.add_page(pagina)
                    
                    if len(paginas_encontradas) > 1:
                        nome_arquivo_saida = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_pag{num_pagina+1}.pdf"
                    else:
                        nome_arquivo_saida = os.path.basename(pdf_path)
                    
                    caminho_saida = os.path.join(output_dir, nome_arquivo_saida)
                    with open(caminho_saida, "wb") as novo_pdf:
                        escritor.write(novo_pdf)
                    print(f"✅ Arquivo salvo: {caminho_saida}")
    except Exception as e:
        print(f"Erro ao processar {pdf_path}: {e}")

def processar_holerites_em_paralelo(input_dir, nome_colaborador, output_dir, ano_admissao, ano_demissao):
    """Usa ProcessPoolExecutor para otimizar processamento paralelo."""
    os.makedirs(output_dir, exist_ok=True)
    
    anos_permitidos = [str(ano) for ano in range(ano_admissao, ano_demissao + 1)]
    pastas_validas = [os.path.join(input_dir, "HOLERITES", pasta) for pasta in os.listdir(os.path.join(input_dir, "HOLERITES")) if any(ano in pasta for ano in anos_permitidos)]
    
    arquivos_pdf = []
    for pasta in pastas_validas:
        arquivos_pdf.extend([os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith(".pdf")])
    
    print("📋 Arquivos a serem processados:", arquivos_pdf)
    
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        executor.map(processar_holerite, arquivos_pdf, [nome_colaborador]*len(arquivos_pdf), [output_dir]*len(arquivos_pdf))
    
    for arquivo in os.listdir(output_dir):
        if "_pag1.pdf" in arquivo:
            try:
                os.remove(os.path.join(output_dir, arquivo))
                print(f"🗑️ Arquivo removido: {arquivo}")
            except Exception as e:
                print(f"Erro ao remover {arquivo}: {e}")
    
    for arquivo in os.listdir(output_dir):
        if "_pag" in arquivo:
            caminho_antigo = os.path.join(output_dir, arquivo)
            novo_nome = arquivo.split("_pag")[0] + ".pdf"
            caminho_novo = os.path.join(output_dir, novo_nome)
            try:
                os.rename(caminho_antigo, caminho_novo)
                print(f"🔄 Arquivo renomeado: {arquivo} -> {novo_nome}")
            except Exception as e:
                print(f"Erro ao renomear {arquivo}: {e}")

def compactar_resultado(output_dir, zip_output):
    """Cria um ZIP com os arquivos filtrados."""
    with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                zipf.write(os.path.join(root, file), file)
    print(f"📦 Arquivos compactados em: {zip_output}")
    print("📋 Conteúdo do ZIP:", os.listdir(output_dir))

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files or 'name' not in request.form or 'admissao' not in request.form or 'demissao' not in request.form:
            return "Erro: Todos os campos são obrigatórios."
        
        file = request.files['file']
        nome_colaborador = request.form['name'].strip()
        ano_admissao = int(request.form['admissao'].strip())
        ano_demissao = int(request.form['demissao'].strip())
        
        if file.filename == '':
            return "Erro: Nenhum arquivo selecionado."
        
        zip_path = "uploaded.zip"
        file.save(zip_path)
        
        temp_extract_dir = "temp_holerites"
        output_dir = os.path.join("output", nome_colaborador)
        output_zip = f"{nome_colaborador}.zip"
        os.makedirs("output", exist_ok=True)
        
        extrair_arquivos(zip_path, temp_extract_dir)
        processar_holerites_em_paralelo(temp_extract_dir, nome_colaborador, output_dir, ano_admissao, ano_demissao)
        compactar_resultado(output_dir, output_zip)
        
        return send_file(output_zip, as_attachment=True)
    
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)