import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, Save, Loader2, Eye, Edit, X } from "lucide-react";

interface Lembrete {
  dias_antes: number;
  mensagem: string;
  enviar_segunda_via: boolean;
  envio_pdf: boolean;
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
        envio_pdf: true,
      },
      {
        dias_antes: 1,
        mensagem: "Olá {cliente}, seu boleto vence amanhã! Valor: R$ {valor}",
        enviar_segunda_via: true,
        envio_pdf: true,
      },
    ],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingLembrete, setEditingLembrete] = useState<Lembrete | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${API_URL}/cobranca-config`);
      const data = await response.json();
      console.log('📥 Configuração carregada do backend:', data);
      console.log('📋 Lembretes carregados:', data.lembretes);
      
      // Garantir que lembretes tenham os campos novos
      if (data.lembretes) {
        const lembretesComCampos = data.lembretes.map((lembrete: any) => ({
          ...lembrete,
          envio_pdf: lembrete.envio_pdf ?? false,
        }));
        data.lembretes = lembretesComCampos;
        console.log('📋 Lembretes com campos novos:', lembretesComCampos);
      }
      
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
    console.log('📋 Lembretes sendo salvos:', config.lembretes);
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
          envio_pdf: true,
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

  const previewMessage = (mensagem: string) => {
    return mensagem
      .replace(/{cliente}/g, "João Silva")
      .replace(/{dias}/g, "5")
      .replace(/{valor}/g, "R$ 1.234,56")
      .replace(/{vencimento}/g, "15/07/2026");
  };

  const openEditModal = (index: number) => {
    setEditingIndex(index);
    setEditingLembrete({ ...config.lembretes[index] });
  };

  const closeEditModal = () => {
    setEditingIndex(null);
    setEditingLembrete(null);
  };

  const saveEditedLembrete = () => {
    if (editingIndex !== null && editingLembrete) {
      const newLembretes = [...config.lembretes];
      newLembretes[editingIndex] = editingLembrete;
      setConfig({ ...config, lembretes: newLembretes });
      closeEditModal();
    }
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
            <div key={index} className="flex items-center justify-between border rounded-lg p-4 hover:bg-muted/50">
              <div className="flex-1">
                <div className="flex items-center gap-4">
                  <span className="font-semibold">Lembrete #{index + 1}</span>
                  <Badge variant="outline">
                    {lembrete.dias_antes > 0 ? `+${lembrete.dias_antes} dias após` : 
                     lembrete.dias_antes < 0 ? `${lembrete.dias_antes} dias antes` : 
                     'Dia do vencimento'}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-1 truncate max-w-md">
                  {lembrete.mensagem}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  {lembrete.envio_pdf && <Badge variant="secondary">PDF</Badge>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openEditModal(index)}
                >
                  <Edit className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeLembrete(index)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
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

      {/* Modal de Edição de Lembrete */}
      {editingLembrete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Editar Lembrete #{editingIndex! + 1}</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={closeEditModal}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Dias em relação ao vencimento</Label>
                <Input
                  type="number"
                  value={editingLembrete.dias_antes}
                  onChange={(e) => setEditingLembrete({ ...editingLembrete, dias_antes: parseInt(e.target.value) || 0 })}
                  placeholder="Ex: -5, 0, 5"
                />
                <p className="text-xs text-muted-foreground">
                  Negativo = antes (ex: -5), 0 = dia do vencimento, Positivo = depois (ex: 5)
                </p>
              </div>

              <div className="space-y-2">
                <Label>Mensagem do lembrete</Label>
                <Textarea
                  value={editingLembrete.mensagem}
                  onChange={(e) => setEditingLembrete({ ...editingLembrete, mensagem: e.target.value })}
                  placeholder="Use {cliente}, {dias}, {valor}, {vencimento} como variáveis"
                  rows={4}
                  className="resize-none"
                />
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPreviewIndex(previewIndex === editingIndex ? null : editingIndex)}
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    {previewIndex === editingIndex ? "Ocultar pré-visualização" : "Pré-visualizar"}
                  </Button>
                </div>
                {previewIndex === editingIndex && (
                  <div className="bg-muted p-3 rounded-md text-sm">
                    <p className="font-medium mb-1">Pré-visualização:</p>
                    <p className="whitespace-pre-wrap">{previewMessage(editingLembrete.mensagem)}</p>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <Label>Opções de Envio</Label>
                
                <div className="flex items-center justify-between border rounded-lg p-4">
                  <div>
                    <p className="font-medium">Enviar PDF do boleto</p>
                    <p className="text-sm text-muted-foreground">Anexar arquivo PDF do boleto na mensagem</p>
                  </div>
                  <Switch
                    checked={editingLembrete.envio_pdf}
                    onCheckedChange={(checked) => setEditingLembrete({ ...editingLembrete, envio_pdf: checked })}
                  />
                </div>

                <div className="flex items-center justify-between border rounded-lg p-4">
                  <div>
                    <p className="font-medium">Enviar segunda via (legado)</p>
                    <p className="text-sm text-muted-foreground">Opção original de envio de boleto</p>
                  </div>
                  <Switch
                    checked={editingLembrete.enviar_segunda_via}
                    onCheckedChange={(checked) => setEditingLembrete({ ...editingLembrete, enviar_segunda_via: checked })}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={saveEditedLembrete} className="flex-1">
                  <Save className="w-4 h-4 mr-2" />
                  Salvar Alterações
                </Button>
                <Button onClick={closeEditModal} variant="outline" className="flex-1">
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default CobrancaConfig;
