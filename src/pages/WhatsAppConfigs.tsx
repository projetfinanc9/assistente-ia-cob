import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { 
  RefreshCw, Phone, Plus, Edit, Trash2, CheckCircle, XCircle, AlertCircle, Save
} from 'lucide-react';

interface WhatsAppConfig {
  id: number;
  nome: string;
  whatsapp_phone_number_id: string;
  whatsapp_token: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export default function WhatsAppConfigs() {
  const [configs, setConfigs] = useState<WhatsAppConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<WhatsAppConfig | null>(null);
  const [saving, setSaving] = useState(false);
  
  // Form states
  const [nome, setNome] = useState('');
  const [whatsappPhoneNumberId, setWhatsappPhoneNumberId] = useState('');
  const [whatsappToken, setWhatsappToken] = useState('');
  const [ativo, setAtivo] = useState(true);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/whatsapp-configs`);
      const data = await response.json();
      
      if (data.success) {
        setConfigs(data.data);
      } else {
        setError(data.error || 'Erro ao carregar configurações');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  const openCreateDialog = () => {
    setEditingConfig(null);
    setNome('');
    setWhatsappPhoneNumberId('');
    setWhatsappToken('');
    setAtivo(true);
    setDialogOpen(true);
  };

  const openEditDialog = (config: WhatsAppConfig) => {
    setEditingConfig(config);
    setNome(config.nome);
    setWhatsappPhoneNumberId(config.whatsapp_phone_number_id);
    setWhatsappToken(''); // Não mostrar token existente por segurança
    setAtivo(config.ativo);
    setDialogOpen(true);
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      setError(null);
      
      const payload = {
        nome,
        whatsapp_phone_number_id: whatsappPhoneNumberId,
        whatsapp_token: whatsappToken || undefined
      };

      let response;
      if (editingConfig) {
        // Atualizar
        response = await fetch(`${API_URL}/whatsapp-configs/${editingConfig.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...payload,
            ativo
          })
        });
      } else {
        // Criar
        response = await fetch(`${API_URL}/whatsapp-configs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess(editingConfig ? 'Configuração atualizada com sucesso' : 'Configuração criada com sucesso');
        setDialogOpen(false);
        await loadConfigs();
      } else {
        setError(data.error || 'Erro ao salvar configuração');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setSaving(false);
    }
  };

  const deleteConfig = async (configId: number) => {
    if (!confirm('Tem certeza que deseja deletar esta configuração?')) return;
    
    try {
      const response = await fetch(`${API_URL}/whatsapp-configs/${configId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess('Configuração deletada com sucesso');
        await loadConfigs();
      } else {
        setError(data.error || 'Erro ao deletar configuração');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    }
  };

  const activeCount = configs.filter(c => c.ativo).length;
  const totalCount = configs.length;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Phone className="h-8 w-8" />
            Configurações WhatsApp
          </h1>
          <p className="text-muted-foreground mt-2">
            Gerencie números WhatsApp Business API para seus empreendimentos
          </p>
        </div>
        <Button onClick={openCreateDialog} className="gap-2">
          <Plus className="h-4 w-4" />
          Nova Configuração
        </Button>
      </div>

      {/* Alertas */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Phone className="h-8 w-8 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{totalCount}</div>
                <div className="text-sm text-muted-foreground">Total</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div>
                <div className="text-2xl font-bold">{activeCount}</div>
                <div className="text-sm text-muted-foreground">Ativas</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <XCircle className="h-8 w-8 text-red-600" />
              <div>
                <div className="text-2xl font-bold">{totalCount - activeCount}</div>
                <div className="text-sm text-muted-foreground">Inativas</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Lista de Configurações */}
      <Card>
        <CardHeader>
          <CardTitle>Configurações Cadastradas</CardTitle>
          <CardDescription>
            {totalCount} configurações disponíveis
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <RefreshCw className="h-8 w-8 mx-auto animate-spin" />
              <p className="mt-2">Carregando...</p>
            </div>
          ) : configs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhuma configuração WhatsApp cadastrada</p>
              <p className="text-sm">
                Clique em "Nova Configuração" para adicionar
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {configs.map((config) => (
                <div 
                  key={config.id} 
                  className={`flex items-center justify-between p-4 border rounded-lg ${
                    config.ativo ? 'bg-green-50/50' : 'bg-gray-50/50'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium text-lg">{config.nome}</h3>
                      {config.ativo ? (
                        <Badge className="bg-green-100 text-green-800">Ativa</Badge>
                      ) : (
                        <Badge variant="secondary">Inativa</Badge>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      Phone ID: {config.whatsapp_phone_number_id}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Criada em: {new Date(config.created_at).toLocaleDateString('pt-BR')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openEditDialog(config)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => deleteConfig(config.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog de Criação/Edição */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              {editingConfig ? 'Editar Configuração' : 'Nova Configuração'}
            </DialogTitle>
            <DialogDescription>
              Configure os dados do WhatsApp Business API
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="nome">Nome da Configuração</Label>
              <Input
                id="nome"
                placeholder="Ex: Residencial Alfa, Comercial Beta"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Nome descritivo para identificar esta configuração
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="whatsapp-phone-number-id">WhatsApp Phone Number ID</Label>
              <Input
                id="whatsapp-phone-number-id"
                placeholder="Ex: 1197028640168563"
                value={whatsappPhoneNumberId}
                onChange={(e) => setWhatsappPhoneNumberId(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                ID do número de telefone do WhatsApp Business API (Meta)
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="whatsapp-token">WhatsApp Token</Label>
              <Input
                id="whatsapp-token"
                type="password"
                placeholder={editingConfig ? "Deixe em branco para manter o atual" : "Token do WhatsApp"}
                value={whatsappToken}
                onChange={(e) => setWhatsappToken(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Token de acesso do WhatsApp. Será criptografado automaticamente.
              </p>
            </div>
            
            <div className="flex items-center space-x-2">
              <Switch
                id="ativo"
                checked={ativo}
                onCheckedChange={setAtivo}
              />
              <Label htmlFor="ativo">Configuração Ativa</Label>
            </div>
            
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancelar
              </Button>
              <Button
                onClick={saveConfig}
                disabled={saving}
                className="gap-2"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Salvando...' : 'Salvar'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
