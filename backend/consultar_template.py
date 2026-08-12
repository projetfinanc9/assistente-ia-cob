import os
import requests
import logging
import json

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")

def listar_templates():
    """
    Lista todos os templates WhatsApp disponíveis para o número configurado
    """
    if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_TOKEN:
        print("❌ WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_TOKEN não configurados")
        return None
    
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/message_templates"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"📋 Listando templates para phone number ID: {WHATSAPP_PHONE_NUMBER_ID}")
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Erro ao listar templates: {response.text}")
            return None
        
        data = response.json()
        templates = data.get("data", [])
        
        print(f"\n✅ {len(templates)} templates encontrados:\n")
        
        for template in templates:
            name = template.get("name")
            status = template.get("status")
            category = template.get("category")
            language = template.get("language")
            
            print(f"📝 Nome: {name}")
            print(f"   Status: {status}")
            print(f"   Categoria: {category}")
            print(f"   Idioma: {language}")
            print()
        
        return templates
        
    except Exception as e:
        print(f"❌ Erro ao listar templates: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    listar_templates()
