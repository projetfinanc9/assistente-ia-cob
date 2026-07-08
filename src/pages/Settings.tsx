import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Save, Check, X, Settings as SettingsIcon, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface SiengeConfig {
  subdomain: string;
  username: string;
  password: string;
}

const Settings = () => {
  const navigate = useNavigate();
  const [config, setConfig] = useState<SiengeConfig>({
    subdomain: "",
    username: "",
    password: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">("idle");

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch("http://localhost:8000/config");
      if (response.ok) {
        const data = await response.json();
        setConfig({
          subdomain: data.subdomain || "",
          username: data.username || "",
          password: data.password || "",
        });
      }
    } catch (error) {
      console.error("Erro ao carregar configurações:", error);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    setSaveStatus("idle");

    try {
      const response = await fetch("http://localhost:8000/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        setSaveStatus("success");
        setTimeout(() => setSaveStatus("idle"), 3000);
      } else {
        setSaveStatus("error");
      }
    } catch (error) {
      console.error("Erro ao salvar configurações:", error);
      setSaveStatus("error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/test-sienge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setSaveStatus("success");
          alert("✅ Conexão com Sienge estabelecida com sucesso!");
        } else {
          setSaveStatus("error");
          alert(`❌ Erro: ${data.error}`);
        }
      } else {
        setSaveStatus("error");
        alert("❌ Erro ao testar conexão");
      }
    } catch (error) {
      console.error("Erro ao testar conexão:", error);
      setSaveStatus("error");
      alert("❌ Erro ao testar conexão");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate("/")} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Button>
          <div className="flex items-center gap-2">
            <SettingsIcon className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold">Configurações</h1>
          </div>
          <div className="w-20" />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-2">Configurações do Sienge</h2>
            <p className="text-muted-foreground">
              Configure as credenciais da API do Sienge para integração
            </p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Credenciais da API</CardTitle>
              <CardDescription>
                Informações necessárias para conectar ao Sienge Plataforma
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Subdomain */}
              <div className="space-y-2">
                <Label htmlFor="subdomain">Subdomínio</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="subdomain"
                    placeholder="Ex: mds"
                    value={config.subdomain}
                    onChange={(e) => setConfig({ ...config, subdomain: e.target.value })}
                    className="flex-1"
                  />
                  <span className="text-sm text-muted-foreground">.sienge.com.br</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Digite apenas o subdomínio. Exemplo: se sua URL é mds.sienge.com.br, digite apenas "mds"
                </p>
              </div>

              {/* Username */}
              <div className="space-y-2">
                <Label htmlFor="username">Usuário da API</Label>
                <Input
                  id="username"
                  placeholder="Ex: cctcontrol-api"
                  value={config.username}
                  onChange={(e) => setConfig({ ...config, username: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Usuário de integração fornecido pelo Sienge
                </p>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password">Senha/Token da API</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Digite sua senha/token"
                  value={config.password}
                  onChange={(e) => setConfig({ ...config, password: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Senha ou token de autenticação da API
                </p>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <Button
                  onClick={handleSave}
                  disabled={isLoading}
                  className="flex-1"
                >
                  {isLoading ? (
                    "Salvando..."
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Salvar Configurações
                    </>
                  )}
                </Button>
                <Button
                  onClick={handleTestConnection}
                  disabled={isLoading || !config.subdomain || !config.username || !config.password}
                  variant="outline"
                  className="flex-1"
                >
                  {isLoading ? "Testando..." : "Testar Conexão"}
                </Button>
              </div>

              {/* Status */}
              {saveStatus === "success" && (
                <div className="flex items-center gap-2 text-green-600 bg-green-50 p-3 rounded-lg">
                  <Check className="h-4 w-4" />
                  <span className="text-sm">Configurações salvas com sucesso!</span>
                </div>
              )}
              {saveStatus === "error" && (
                <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-lg">
                  <X className="h-4 w-4" />
                  <span className="text-sm">Erro ao salvar configurações</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card className="bg-muted/50">
            <CardHeader>
              <CardTitle className="text-lg">💡 Onde encontrar essas informações?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
                <li>Acesse o painel do Sienge Plataforma</li>
                <li>Navegue para Configurações, depois Integrações, depois API</li>
                <li>Crie ou use um usuário de integração existente</li>
                <li>Copie o subdomínio, usuário e senha/token</li>
              </ol>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default Settings;
