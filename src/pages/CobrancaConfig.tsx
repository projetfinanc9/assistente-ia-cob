import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Plus, Trash2, Save, Loader2 } from "lucide-react";

interface Lembrete {
  dias_antes: number;
  mensagem: string;
  enviar_segunda_via: boolean;
}

interface ConfigCobranca {
  ativo: boolean;
  horario_execucao: string;
  lembretes: Lembrete[];
}

const CobrancaConfig = () => {
  const [config, setConfig] = useState<ConfigCobranca>({
    ativo: false,
    horario_execucao: "09:00",
    lembretes: [
      {
        dias_antes: 5,
        mensagem: "Olá {cliente}, seu boleto vence em {dias} dias. Valor: R$ {valor}",
        enviar_segunda_via: true,
      },
      {
        dias_antes: 1,
        mensagem: "Olá {cliente}, seu boleto vence amanhã! Valor: R$ {valor}",
        enviar_segunda_via: true,
      },
    ],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${API_URL}/cobranca-config`);
      const data = await response.json();
      setConfig(data);
    } catch (error) {
      console.error('Erro ao carregar configuração:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    setMessage('');
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    console.log('📝 Tentando salvar configuração:', config);
    console.log('🌐 API URL:', API_URL);
    try {
      console.log('📡 Fazendo requisição POST para:', `${API_URL}/cobranca-config`);
      const response = await fetch(`${API_URL}/cobranca-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      console.log('📊 Status da resposta:', response.status);
      const data = await response.json();
      console.log('📦 Dados da resposta:', data);
      if (data.success) {
        setMessage('✅ Configurações salvas com sucesso!');
        // Recarregar configuração do Supabase
        await loadConfig();
      } else {
        setMessage(`❌ Erro: ${data.error}`);
      }
    } catch (error) {
      console.error('❌ Erro ao salvar configurações:', error);
      setMessage('❌ Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  };

  const addLembrete = () => {
    setConfig({
      ...config,
      lembretes: [
        ...config.lembretes,
        {
          dias_antes: 3,
          mensagem: "Lembrete padrão",
          enviar_segunda_via: true,
        },
      ],
    });
  };

  const removeLembrete = (index: number) => {
    setConfig({
      ...config,
      lembretes: config.lembretes.filter((_, i) => i !== index),
    });
  };

  const updateLembrete = (index: number, field: keyof Lembrete, value: any) => {
    const newLembretes = [...config.lembretes];
    newLembretes[index] = { ...newLembretes[index], [field]: value };
    setConfig({ ...config, lembretes: newLembretes });
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Configuração de Cobrança Automática</h1>
        <p className="text-muted-foreground">
          Configure lembretes automáticos de cobrança via WhatsApp
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Status do Sistema</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="ativo">Cobrança Automática</Label>
              <p className="text-sm text-muted-foreground">
                Ative para enviar lembretes automaticamente
              </p>
            </div>
            <Switch
              id="ativo"
              checked={config.ativo}
              onCheckedChange={(checked) => setConfig({ ...config, ativo: checked })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="horario">Horário de Execução</Label>
            <Input
              id="horario"
              type="time"
              value={config.horario_execucao}
              onChange={(e) => setConfig({ ...config, horario_execucao: e.target.value })}
            />
            <p className="text-sm text-muted-foreground">
              Horário em que o sistema verificará boletos vencendo todos os dias
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Lembretes de Cobrança</CardTitle>
          <CardDescription>
            Configure quando e como enviar lembretes de cobrança
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {config.lembretes.map((lembrete, index) => (
            <div key={index} className="border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Lembrete #{index + 1}</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeLembrete(index)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>

              <div className="space-y-2">
                <Label>Dias antes do vencimento</Label>
                <Input
                  type="number"
                  value={lembrete.dias_antes}
                  onChange={(e) => updateLembrete(index, 'dias_antes', parseInt(e.target.value))}
                />
              </div>

              <div className="space-y-2">
                <Label>Mensagem do lembrete</Label>
                <Input
                  value={lembrete.mensagem}
                  onChange={(e) => updateLembrete(index, 'mensagem', e.target.value)}
                  placeholder="Use {cliente}, {dias}, {valor} como variáveis"
                />
              </div>

              <div className="flex items-center justify-between">
                <Label>Enviar segunda via do boleto</Label>
                <Switch
                  checked={lembrete.enviar_segunda_via}
                  onCheckedChange={(checked) => updateLembrete(index, 'enviar_segunda_via', checked)}
                />
              </div>
            </div>
          ))}

          <Button onClick={addLembrete} variant="outline" className="w-full">
            <Plus className="w-4 h-4 mr-2" />
            Adicionar Lembrete
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <Button onClick={saveConfig} disabled={saving} className="w-full">
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Salvar Configurações
                </>
              )}
            </Button>

            {message && (
              <div className={`text-center text-sm ${message.startsWith('✅') ? 'text-green-600' : 'text-red-600'}`}>
                {message}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Variáveis Disponíveis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p><code>{"{cliente}"}</code> - Nome do cliente</p>
          <p><code>{"{dias}"}</code> - Dias até o vencimento</p>
          <p><code>{"{valor}"}</code> - Valor do boleto</p>
          <p><code>{"{vencimento}"}</code> - Data de vencimento</p>
        </CardContent>
      </Card>
    </div>
  );
};

export default CobrancaConfig;
