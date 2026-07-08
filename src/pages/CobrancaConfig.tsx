import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Bell, Plus, Trash2, Save } from "lucide-react";

interface Lembrete {
  dias_antes: number;
  mensagem: string;
  enviar_segunda_via: boolean;
}

interface ConfiguracaoCobranca {
  ativo: boolean;
  lembretes: Lembrete[];
}

export default function CobrancaConfig() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<ConfiguracaoCobranca>({
    ativo: false,
    lembretes: [
      {
        dias_antes: 5,
        mensagem: 'Olá {cliente}, seu boleto vence em {dias} dias. Valor: R$ {valor}',
        enviar_segunda_via: true,
      },
      {
        dias_antes: 1,
        mensagem: 'Olá {cliente}, seu boleto vence amanhã! Valor: R$ {valor}',
        enviar_segunda_via: true,
      },
    ],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch('http://localhost:8000/cobranca-config');
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
    try {
      const response = await fetch('http://localhost:8000/cobranca-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await response.json();
      if (data.success) {
        setMessage('✅ Configurações salvas com sucesso!');
      } else {
        setMessage(`❌ Erro: ${data.error}`);
      }
    } catch (error) {
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
          mensagem: 'Olá {cliente}, seu boleto vence em {dias} dias. Valor: R$ {valor}',
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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div>Carregando...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate('/')} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Button>
          <div className="flex items-center gap-2">
            <Bell className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold">Cobrança Automática</h1>
          </div>
          <div className="w-20" />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-2">Configuração de Cobrança Automática</h2>
            <p className="text-muted-foreground">
              Configure lembretes automáticos para clientes com boletos próximos ao vencimento
            </p>
          </div>

          {/* Ativar/Desativar */}
          <Card>
            <CardHeader>
              <CardTitle>Status do Sistema</CardTitle>
              <CardDescription>
                Ative ou desative o sistema de cobrança automática
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.ativo}
                  onChange={(e) => setConfig({ ...config, ativo: e.target.checked })}
                  className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-lg font-semibold">
                  Ativar cobrança automática
                </span>
              </label>
              <p className="text-muted-foreground mt-2 text-sm">
                Quando ativado, o sistema enviará lembretes automáticos para clientes com boletos próximos ao vencimento.
              </p>
            </CardContent>
          </Card>

          {/* Lembretes */}
          <Card>
            <CardHeader>
              <CardTitle>Lembretes</CardTitle>
              <CardDescription>
                Configure múltiplos lembretes com diferentes períodos antes do vencimento
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {config.lembretes.map((lembrete, index) => (
                <div
                  key={index}
                  className="border rounded-lg p-4 space-y-4"
                >
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold">Lembrete #{index + 1}</h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeLembrete(index)}
                      className="text-red-500 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <Label htmlFor={`dias-${index}`}>Dias antes do vencimento</Label>
                      <Input
                        id={`dias-${index}`}
                        type="number"
                        value={lembrete.dias_antes}
                        onChange={(e) =>
                          updateLembrete(index, 'dias_antes', parseInt(e.target.value) || 0)
                        }
                      />
                    </div>

                    <div>
                      <Label htmlFor={`mensagem-${index}`}>Mensagem</Label>
                      <textarea
                        id={`mensagem-${index}`}
                        value={lembrete.mensagem}
                        onChange={(e) =>
                          updateLembrete(index, 'mensagem', e.target.value)
                        }
                        rows={3}
                        className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-primary resize-none bg-background"
                        placeholder="Use {cliente}, {valor}, {dias} como variáveis"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Variáveis disponíveis: {'{cliente}'}, {'{valor}'}, {'{dias}'}, {'{vencimento}'}
                      </p>
                    </div>

                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={lembrete.enviar_segunda_via}
                        onChange={(e) =>
                          updateLembrete(index, 'enviar_segunda_via', e.target.checked)
                        }
                        className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <span className="text-sm">
                        Enviar segunda via do boleto junto com o lembrete
                      </span>
                    </label>
                  </div>
                </div>
              ))}

              <Button
                onClick={addLembrete}
                variant="outline"
                className="w-full gap-2"
              >
                <Plus className="h-4 w-4" />
                Adicionar Lembrete
              </Button>
            </CardContent>
          </Card>

          {/* Mensagem de feedback */}
          {message && (
            <div className={`p-4 rounded-lg ${
              message.includes('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              {message}
            </div>
          )}

          {/* Botões de ação */}
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => navigate('/')}
            >
              Cancelar
            </Button>
            <Button
              onClick={saveConfig}
              disabled={saving}
              className="gap-2"
            >
              {saving ? 'Salvando...' : (
                <>
                  <Save className="h-4 w-4" />
                  Salvar Configurações
                </>
              )}
            </Button>
          </div>

          {/* Informações */}
          <Card className="bg-muted/50">
            <CardHeader>
              <CardTitle className="text-lg">💡 Informações</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-muted-foreground space-y-2">
                <li>• O sistema verificará automaticamente boletos próximos ao vencimento</li>
                <li>• Você pode configurar quantos lembretes quiser</li>
                <li>• Cada lembrete pode ter uma mensagem personalizada</li>
                <li>• Opção de enviar segunda via do boleto automaticamente</li>
                <li>• As configurações são salvas e persistem após reiniciar o sistema</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
