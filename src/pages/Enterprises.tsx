import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, Building2, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

interface Enterprise {
  id: number;
  enterprise_id: number;
  enterprise_name: string;
  enterprise_type: number;
  company_id: number;
  ativo: boolean;
  building_status?: string;
  cost_center_status?: string;
  building_enabled_for_integration?: boolean;
  created_at: string;
  updated_at: string;
}

interface SyncLog {
  id: number;
  data_sincronizacao: string;
  total_empreendimentos: number;
  novos_empreendimentos: number;
  empreendimentos_atualizados: number;
  erros: number;
  detalhes_erro?: string;
  duracao_segundos: number;
}

export default function Enterprises() {
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    loadEnterprises();
    loadSyncLogs();
  }, []);

  const loadEnterprises = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/enterprises`);
      const data = await response.json();
      
      if (data.success) {
        setEnterprises(data.data);
      } else {
        setError(data.error || 'Erro ao carregar empreendimentos');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  const loadSyncLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/enterprises/logs?limit=5`);
      const data = await response.json();
      
      if (data.success) {
        setSyncLogs(data.data);
      }
    } catch (err) {
      console.error('Erro ao carregar logs:', err);
    }
  };

  const syncEnterprises = async () => {
    try {
      setSyncing(true);
      setError(null);
      setSuccess(null);
      
      const response = await fetch(`${API_URL}/enterprises/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess(data.message);
        await loadEnterprises();
        await loadSyncLogs();
      } else {
        setError(data.error || 'Erro ao sincronizar empreendimentos');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setSyncing(false);
    }
  };

  const toggleEnterpriseStatus = async (enterpriseId: number, currentStatus: boolean) => {
    try {
      const response = await fetch(`${API_URL}/enterprises/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enterprise_id: enterpriseId,
          ativo: !currentStatus
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadEnterprises();
        setSuccess(`Empreendimento ${!currentStatus ? 'ativado' : 'desativado'} com sucesso`);
      } else {
        setError(data.error || 'Erro ao atualizar status');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    }
  };

  const getEnterpriseTypeLabel = (type: number) => {
    const types = {
      1: 'Obra e Centro de custo',
      2: 'Obra',
      3: 'Centro de custo',
      4: 'Centro de custo associado a obra'
    };
    return types[type as keyof typeof types] || 'Desconhecido';
  };

  const getBuildingStatusLabel = (status?: string) => {
    if (!status) return null;
    
    const labels = {
      'COST_ESTIMATING': 'Orçamento',
      'IN_PROGRESS': 'Em andamento',
      'FINISHED_WITH_FINANCIAL_PENDENCIES': 'Encerrada com pendências',
      'FINISHED_WITHOUT_FINANCIAL_PENDENCIES': 'Encerrada sem pendências'
    };
    
    const colors = {
      'COST_ESTIMATING': 'bg-blue-100 text-blue-800',
      'IN_PROGRESS': 'bg-green-100 text-green-800',
      'FINISHED_WITH_FINANCIAL_PENDENCIES': 'bg-yellow-100 text-yellow-800',
      'FINISHED_WITHOUT_FINANCIAL_PENDENCIES': 'bg-gray-100 text-gray-800'
    };
    
    return (
      <Badge className={colors[status as keyof typeof colors] || 'bg-gray-100'}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    );
  };

  const getCostCenterStatusLabel = (status?: string) => {
    if (!status) return null;
    
    const labels = {
      'ACTIVE': 'Ativo',
      'INACTIVE_WITH_PENDENCIES': 'Inativo com pendência',
      'INACTIVE_WITHOUT_PENDENCIES': 'Inativo sem pendência'
    };
    
    const colors = {
      'ACTIVE': 'bg-green-100 text-green-800',
      'INACTIVE_WITH_PENDENCIES': 'bg-red-100 text-red-800',
      'INACTIVE_WITHOUT_PENDENCIES': 'bg-gray-100 text-gray-800'
    };
    
    return (
      <Badge className={colors[status as keyof typeof colors] || 'bg-gray-100'}>
        {labels[status as keyof typeof labels] || status}
      </Badge>
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Building2 className="h-8 w-8" />
            Empreendimentos
          </h1>
          <p className="text-muted-foreground mt-2">
            Configure quais empreendimentos devem receber cobranças automáticas
          </p>
        </div>
        <Button 
          onClick={syncEnterprises} 
          disabled={syncing}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Sincronizando...' : 'Atualizar Empreendimentos'}
        </Button>
      </div>

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

      {/* Logs de Sincronização */}
      {syncLogs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Últimas Sincronizações
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {syncLogs.map((log) => (
                <div key={log.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="text-sm">
                      <div className="font-medium">
                        {new Date(log.data_sincronizacao).toLocaleString('pt-BR')}
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {log.total_empreendimentos} total • {log.novos_empreendimentos} novos • {log.empreendimentos_atualizados} atualizados
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {log.erros > 0 ? (
                      <Badge variant="destructive">{log.erros} erros</Badge>
                    ) : (
                      <Badge className="bg-green-100 text-green-800">Sucesso</Badge>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {log.duracao_segundos.toFixed(2)}s
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de Empreendimentos */}
      <Card>
        <CardHeader>
          <CardTitle>Empreendimentos Cadastrados</CardTitle>
          <CardDescription>
            {enterprises.filter(e => e.ativo).length} de {enterprises.length} empreendimentos ativos para cobrança
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-6 w-12" />
                </div>
              ))}
            </div>
          ) : enterprises.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhum empreendimento cadastrado</p>
              <p className="text-sm">Clique em "Atualizar Empreendimentos" para sincronizar com o Sienge</p>
            </div>
          ) : (
            <div className="space-y-4">
              {enterprises.map((enterprise) => (
                <div 
                  key={enterprise.id} 
                  className={`flex items-center justify-between p-4 border rounded-lg transition-colors ${
                    enterprise.ativo ? 'bg-green-50 border-green-200' : 'bg-gray-50'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-semibold text-lg">{enterprise.enterprise_name}</h3>
                      {enterprise.ativo && (
                        <Badge className="bg-green-100 text-green-800">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Ativo
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span>ID: {enterprise.enterprise_id}</span>
                      <span>•</span>
                      <span>{getEnterpriseTypeLabel(enterprise.enterprise_type)}</span>
                      {enterprise.company_id && (
                        <>
                          <span>•</span>
                          <span>Empresa: {enterprise.company_id}</span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      {getBuildingStatusLabel(enterprise.building_status)}
                      {getCostCenterStatusLabel(enterprise.cost_center_status)}
                      {enterprise.building_enabled_for_integration && (
                        <Badge className="bg-blue-100 text-blue-800">
                          Integração habilitada
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-sm text-muted-foreground">
                      <div>Atualizado em</div>
                      <div>{new Date(enterprise.updated_at).toLocaleDateString('pt-BR')}</div>
                    </div>
                    <Switch
                      checked={enterprise.ativo}
                      onCheckedChange={() => toggleEnterpriseStatus(enterprise.enterprise_id, enterprise.ativo)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}