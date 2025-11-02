# validador_fiscal/tools/email_sender.py
"""
Envio de Email com Relatório Excel
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Dict, List


def enviar_relatorio_email(
    excel_path: str,
    relatorio: Dict,
    destinatarios: List[str],
    smtp_config: Dict = None
):
    """
    Envia relatório por email
    
    Args:
        excel_path: Caminho do Excel
        relatorio: Dict com resumo
        destinatarios: Lista de emails
        smtp_config: Config SMTP (opcional)
    """
    
    # Config padrão (ajustar conforme necessário)
    if not smtp_config:
        smtp_config = {
            "servidor": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "porta": int(os.getenv("SMTP_PORT", "587")),
            "usuario": os.getenv("SMTP_USER", "seu_email@gmail.com"),
            "senha": os.getenv("SMTP_PASSWORD", "sua_senha_app")
        }
    
    # Extrair resumo
    metadata = relatorio.get("metadata", {})
    resumo = relatorio.get("resumo_executivo", {})
    conformidade = relatorio.get("analise_conformidade", {})
    
    nf_numero = metadata.get("numero", "SN")
    total_itens = resumo.get("total_itens", 0)
    diverg_total = resumo.get("divergencia_absoluta", 0)
    diverg_pct = resumo.get("divergencia_percentual", 0)
    risco = resumo.get("nivel_risco", "N/A")
    alertas = len(conformidade.get("alertas", []))
    
    # Montar email
    msg = MIMEMultipart()
    msg['From'] = smtp_config["usuario"]
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = f"Relatório Fiscal - NF {nf_numero} - {total_itens:,} itens"
    
    # Corpo do email
    corpo = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #366092;">Relatório de Validação Fiscal</h2>
        
        <p>Prezado(a),</p>
        
        <p>Segue relatório de validação fiscal da <strong>NF {nf_numero}</strong>.</p>
        
        <h3 style="color: #366092;">📊 RESUMO:</h3>
        <ul>
            <li><strong>Itens processados:</strong> {total_itens:,}</li>
            <li><strong>Total declarado:</strong> R$ {resumo.get('total_declarado', 0):,.2f}</li>
            <li><strong>Total calculado:</strong> R$ {resumo.get('total_calculado', 0):,.2f}</li>
            <li><strong>Divergência total:</strong> R$ {diverg_total:,.2f} ({diverg_pct:+.2f}%)</li>
        </ul>
        
        <h3 style="color: {'#FF6B6B' if risco == 'ALTO' else '#FFD93D' if risco == 'MÉDIO' else '#6BCB77'};">
            {'⚠️' if risco != 'BAIXO' else '✅'} Nível de risco: {risco}
        </h3>
        
        {f'<p><strong>⚠️ {alertas} alerta(s) encontrado(s)</strong></p>' if alertas > 0 else '<p>✅ Nenhuma inconsistência crítica</p>'}
        
        <p>Detalhes completos no arquivo Excel anexo.</p>
        
        <hr>
        <p style="color: #666; font-size: 12px;">
            Relatório gerado automaticamente pelo Sistema Validador Fiscal<br>
            Data: {metadata.get('data_validacao', 'N/A')}
        </p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo, 'html'))
    
    # Anexar Excel
    with open(excel_path, "rb") as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(excel_path)}'
        )
        msg.attach(part)
    
    # Enviar
    print(f"📧 Enviando email para: {', '.join(destinatarios)}")
    
    try:
        with smtplib.SMTP(smtp_config["servidor"], smtp_config["porta"]) as server:
            server.starttls()
            server.login(smtp_config["usuario"], smtp_config["senha"])
            server.send_message(msg)
        
        print(f"✅ Email enviado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        print(f"⚠️ Verifique as configurações SMTP no .env")
        return False


# ==================== CONFIGURAÇÃO ====================

def configurar_email_env():
    """
    Cria arquivo .env.email com template
    """
    
    template = """# Configuração de Email - Validador Fiscal

# GMAIL (recomendado)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app

# IMPORTANTE: Para Gmail, use "Senha de App"
# Instruções: https://support.google.com/accounts/answer/185833

# OUTLOOK/HOTMAIL
# SMTP_SERVER=smtp-mail.outlook.com
# SMTP_PORT=587
# SMTP_USER=seu_email@outlook.com
# SMTP_PASSWORD=sua_senha

# Destinatários padrão (separados por vírgula)
EMAIL_DESTINATARIOS=cliente@empresa.com,fiscal@empresa.com
"""
    
    with open(".env.email", "w") as f:
        f.write(template)
    
    print("✅ Arquivo .env.email criado!")
    print("📝 Configure suas credenciais SMTP no arquivo .env.email")


# ==================== TESTE ====================

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DO EMAIL SENDER")
    print("=" * 60)
    
    # Verificar se .env.email existe
    if not os.path.exists(".env.email"):
        print("\n⚠️ Arquivo .env.email não encontrado")
        print("Criando template...")
        configurar_email_env()
    else:
        print("\n✅ Arquivo .env.email encontrado")
    
    print("\n📧 Para testar o envio:")
    print("1. Configure .env.email com suas credenciais")
    print("2. Execute:")
    print("   python -m validador_fiscal.tools.email_sender")