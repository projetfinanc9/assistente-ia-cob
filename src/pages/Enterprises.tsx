import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  RefreshCw, Building2, CheckCircle, XCircle, Clock, AlertCircle,
  Search, Filter, CheckSquare, Square, ChevronDown, ChevronUp,
  MapPin, Building, Calendar, TrendingUp, Phone, Settings, Save
} from 'lucide-react';

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
  address?: string;
  whatsapp_config_id?: number;
  whatsapp_config?: {
    id: number;
    nome: string;
    whatsapp_phone_number_id: string;
    ativo: boolean;
  };
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
  
  // Filtros e busca
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<'name' | 'id' | 'updated'>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedAll, setSelectedAll] = useState(false);
  const [selectedEnterprises, setSelectedEnterprises] = useState<Set<number>>(new Set());
  
  // WhatsApp configuration dialog
  const [whatsappDialogOpen, setWhatsappDialogOpen] = useState(false);
  const [selectedEnterpriseForWhatsapp, setSelectedEnterpriseForWhatsapp] = useState<Enterprise | null>(null);
  const [whatsappConfigs, setWhatsappConfigs] = useState<any[]>([]);
  const [selectedWhatsappConfigId, setSelectedWhatsappConfigId] = useState<number | null>(null);
  const [savingWhatsapp, setSavingWhatsapp] = useState(false);
  const [loadingConfigs, setLoadingConfigs] = useState(false);

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

  const toggleAllSelection = () => {
    if (selectedAll) {
      setSelectedEnterprises(new Set());
    } else {
      setSelectedEnterprises(new Set(filteredEnterprises.map(e => e.enterprise_id)));
    }
    setSelectedAll(!selectedAll);
  };

  const toggleEnterpriseSelection = (enterpriseId: number) => {
    const newSelection = new Set(selectedEnterprises);
    if (newSelection.has(enterpriseId)) {
      newSelection.delete(enterpriseId);
    } else {
      newSelection.add(enterpriseId);
    }
    setSelectedEnterprises(newSelection);
  };

  const bulkActivate = async () => {
    try {
      for (const enterpriseId of selectedEnterprises) {
        await fetch(`${API_URL}/enterprises/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enterprise_id, ativo: true })
        });
      }
      setSelectedEnterprises(new Set());
      setSelectedAll(false);
      await loadEnterprises();
      setSuccess(`${selectedEnterprises.size} empreendimentos ativados`);
    } catch (err) {
      setError('Erro ao ativar empreendimentos');
    }
  };

  const bulkDeactivate = async () => {
    try {
      for (const enterpriseId of selectedEnterprises) {
        await fetch(`${API_URL}/enterprises/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enterprise_id, ativo: false })
        });
      }
      setSelectedEnterprises(new Set());
      setSelectedAll(false);
      await loadEnterprises();
      setSuccess(`${selectedEnterprises.size} empreendimentos desativados`);
    } catch (err) {
      setError('Erro ao desativar empreendimentos');
    }
  };

  const loadWhatsappConfigs = async () => {
    try {
      setLoadingConfigs(true);
      const response = await fetch(`${API_URL}/whatsapp-configs`);
      const data = await response.json();
      
      if (data.success) {
        setWhatsappConfigs(data.data);
      }
    } catch (err) {
      console.error('Erro ao carregar configurações WhatsApp:', err);
    } finally {
      setLoadingConfigs(false);
    }
  };

  const openWhatsappDialog = async (enterprise: Enterprise) => {
    setSelectedEnterpriseForWhatsapp(enterprise);
    setSelectedWhatsappConfigId(enterprise.whatsapp_config_id || null);
    await loadWhatsappConfigs();
    setWhatsappDialogOpen(true);
  };

  const saveWhatsappConfig = async () => {
    if (!selectedEnterpriseForWhatsapp) return;
    
    try {
      setSavingWhatsapp(true);
      setError(null);
      
      const response = await fetch(`${API_URL}/enterprises/whatsapp-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enterprise_id: selectedEnterpriseForWhatsapp.enterprise_id,
          whatsapp_config_id: selectedWhatsappConfigId
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess(selectedWhatsappConfigId ? 'Configuração WhatsApp vinculada com sucesso' : 'Configuração WhatsApp desvinculada com sucesso');
        setWhatsappDialogOpen(false);
        await loadEnterprises();
      } else {
        setError(data.error || 'Erro ao vincular configuração WhatsApp');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setSavingWhatsapp(false);
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

  // Filtrar e ordenar empreendimentos
  const filteredEnterprises = enterprises
    .filter(e => {
      const matchesSearch = e.enterprise_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           e.enterprise_id.toString().includes(searchTerm);
      const matchesType = filterType === 'all' || e.enterprise_type.toString() === filterType;
      const matchesStatus = filterStatus === 'all' || 
                           (filterStatus === 'active' && e.ativo) ||
                           (filterStatus === 'inactive' && !e.ativo);
      return matchesSearch && matchesType && matchesStatus;
    })
    .sort((a, b) => {
      let comparison = 0;
      if (sortField === 'name') {
        comparison = a.enterprise_name.localeCompare(b.enterprise_name);
      } else if (sortField === 'id') {
        comparison = a.enterprise_id - b.enterprise_id;
      } else if (sortField === 'updated') {
        comparison = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

  const handleSort = (field: 'name' | 'id' | 'updated') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const activeCount = enterprises.filter(e => e.ativo).length;
  const totalCount = enterprises.length;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Building2 className="h-8 w-8 text-blue-600" />
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
                <div className="text-sm text-muted-foreground">Ativos</div>
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
                <div className="text-sm text-muted-foreground">Inativos</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <TrendingUp className="h-8 w-8 text-purple-600" />
              <div>
                <div className="text-2xl font-bold">
                  {totalCount > 0 ? ((activeCount / totalCount) * 100).toFixed(0) : 0}%
                </div>
                <div className="text-sm text-muted-foreground">Ativação</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filtros e Busca */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nome ou ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-4 py-2 border rounded-md bg-background"
            >
              <option value="all">Todos os tipos</option>
              <option value="1">Obra e Centro de custo</option>
              <option value="2">Obra</option>
              <option value="3">Centro de custo</option>
              <option value="4">Centro de custo associado a obra</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 border rounded-md bg-background"
            >
              <option value="all">Todos os status</option>
              <option value="active">Ativos</option>
              <option value="inactive">Inativos</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Ações em Massa */}
      {selectedEnterprises.size > 0 && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckSquare className="h-5 w-5 text-blue-600" />
                <span className="font-medium">{selectedEnterprises.size} empreendimentos selecionados</span>
              </div>
              <div className="flex gap-2">
                <Button onClick={bulkActivate} size="sm" className="bg-green-600 hover:bg-green-700">
                  Ativar Todos
                </Button>
                <Button onClick={bulkDeactivate} size="sm" variant="destructive">
                  Desativar Todos
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
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
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Empreendimentos Cadastrados</CardTitle>
              <CardDescription>
                {filteredEnterprises.length} de {enterprises.length} empreendimentos {searchTerm && '(filtrados)'}
              </CardDescription>
            </div>
          </div>
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
          ) : filteredEnterprises.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Building2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Nenhum empreendimento encontrado</p>
              <p className="text-sm">
                {searchTerm ? 'Tente ajustar os filtros' : 'Clique em "Atualizar Empreendimentos" para sincronizar com o Sienge'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="p-3 text-left">
                      <button
                        onClick={toggleAllSelection}
                        className="flex items-center gap-2 hover:text-blue-600"
                      >
                        {selectedAll ? (
                          <CheckSquare className="h-4 w-4" />
                        ) : (
                          <Square className="h-4 w-4" />
                        )}
                      </button>
                    </th>
                    <th className="p-3 text-left cursor-pointer hover:text-blue-600" onClick={() => handleSort('name')}>
                      <div className="flex items-center gap-1">
                        Nome
                        {sortField === 'name' && (sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />)}
                      </div>
                    </th>
                    <th className="p-3 text-left cursor-pointer hover:text-blue-600" onClick={() => handleSort('id')}>
                      <div className="flex items-center gap-1">
                        ID
                        {sortField === 'id' && (sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />)}
                      </div>
                    </th>
                    <th className="p-3 text-left">Tipo</th>
                    <th className="p-3 text-left">Status</th>
                    <th className="p-3 text-left">WhatsApp</th>
                    <th className="p-3 text-left cursor-pointer hover:text-blue-600" onClick={() => handleSort('updated')}>
                      <div className="flex items-center gap-1">
                        Atualizado
                        {sortField === 'updated' && (sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />)}
                      </div>
                    </th>
                    <th className="p-3 text-center">Ativo</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEnterprises.map((enterprise) => (
                    <tr 
                      key={enterprise.id} 
                      className={`border-b hover:bg-gray-50 transition-colors ${
                        enterprise.ativo ? 'bg-green-50/50' : ''
                      }`}
                    >
                      <td className="p-3">
                        <button
                          onClick={() => toggleEnterpriseSelection(enterprise.enterprise_id)}
                          className="hover:text-blue-600"
                        >
                          {selectedEnterprises.has(enterprise.enterprise_id) ? (
                            <CheckSquare className="h-4 w-4" />
                          ) : (
                            <Square className="h-4 w-4" />
                          )}
                        </button>
                      </td>
                      <td className="p-3">
                        <div className="font-medium">{enterprise.enterprise_name}</div>
                        {enterprise.address && (
                          <div className="text-xs text-muted-foreground flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {enterprise.address.substring(0, 50)}...
                          </div>
                        )}
                      </td>
                      <td className="p-3">
                        <Badge variant="outline">{enterprise.enterprise_id}</Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant="secondary">{getEnterpriseTypeLabel(enterprise.enterprise_type)}</Badge>
                      </td>
                      <td className="p-3">
                        <div className="flex flex-wrap gap-1">
                          {getBuildingStatusLabel(enterprise.building_status)}
                          {getCostCenterStatusLabel(enterprise.cost_center_status)}
                        </div>
                      </td>
                      <td className="p-3">
                        {enterprise.whatsapp_config ? (
                          <Badge className="bg-green-100 text-green-800 gap-1 cursor-pointer" onClick={() => openWhatsappDialog(enterprise)}>
                            <Phone className="h-3 w-3" />
                            {enterprise.whatsapp_config.nome}
                          </Badge>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openWhatsappDialog(enterprise)}
                            className="h-6 text-xs"
                          >
                            <Settings className="h-3 w-3 mr-1" />
                            Vincular
                          </Button>
                        )}
                      </td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {new Date(enterprise.updated_at).toLocaleDateString('pt-BR')}
                      </td>
                      <td className="p-3 text-center">
                        <Switch
                          checked={enterprise.ativo}
                          onCheckedChange={() => toggleEnterpriseStatus(enterprise.enterprise_id, enterprise.ativo)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* WhatsApp Configuration Dialog */}
      <Dialog open={whatsappDialogOpen} onOpenChange={setWhatsappDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Vincular Configuração WhatsApp
            </DialogTitle>
            <DialogDescription>
              Selecione uma configuração WhatsApp para este empreendimento
            </DialogDescription>
          </DialogHeader>
          
          {selectedEnterpriseForWhatsapp && (
            <div className="space-y-4">
              <div className="text-sm font-medium">
                Empreendimento: {selectedEnterpriseForWhatsapp.enterprise_name}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="whatsapp-config">Configuração WhatsApp</Label>
                {loadingConfigs ? (
                  <div className="text-sm text-muted-foreground">Carregando configurações...</div>
                ) : (
                  <select
                    id="whatsapp-config"
                    value={selectedWhatsappConfigId || ''}
                    onChange={(e) => setSelectedWhatsappConfigId(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border rounded-md bg-background"
                  >
                    <option value="">Nenhuma (usar configuração global)</option>
                    {whatsappConfigs
                      .filter(config => config.ativo)
                      .map((config) => (
                        <option key={config.id} value={config.id}>
                          {config.nome} ({config.whatsapp_phone_number_id})
                        </option>
                      ))}
                  </select>
                )}
                <p className="text-xs text-muted-foreground">
                  Selecione uma configuração ou deixe vazio para usar a configuração global
                </p>
              </div>
              
              <div className="flex justify-end gap-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => setWhatsappDialogOpen(false)}
                >
                  Cancelar
                </Button>
                <Button
                  onClick={saveWhatsappConfig}
                  disabled={savingWhatsapp}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {savingWhatsapp ? 'Salvando...' : 'Salvar'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}