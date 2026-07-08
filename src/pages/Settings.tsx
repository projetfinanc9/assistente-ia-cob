import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Settings as SettingsIcon, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

const Settings = () => {
  const [config, setConfig] = useState({
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
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${API_URL}/config`);
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
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    try {
      const response = await fetch(`${API_URL}/config`, {
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
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${API_URL}/test-sienge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setSaveStatus("success");
          alert("✅ Conexão estabelecida com sucesso!");
        } else {
          setSaveStatus("error");
          alert(`❌ Erro: ${data.error}`);
        }
      } else {
        setSaveStatus("error");
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">Configurações do Sienge</h1>
            <p className="text-muted-foreground">
              Configure suas credenciais do Sienge para integração com o sistema
            </p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="w-5 h-5" />
                Credenciais da API
              </CardTitle>
              <CardDescription>
                Insira as informações de acesso à API do Sienge
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subdomain">Subdomínio</Label>
                <Input
                  id="subdomain"
                  placeholder="ex: minhaempresa"
                  value={config.subdomain}
                  onChange={(e) => setConfig({ ...config, subdomain: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="username">Usuário</Label>
                <Input
                  id="username"
                  placeholder="ex: admin@minhaempresa.com"
                  value={config.username}
                  onChange={(e) => setConfig({ ...config, username: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={config.password}
                  onChange={(e) => setConfig({ ...config, password: e.target.value })}
                />
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  onClick={handleSave}
                  disabled={isLoading}
                  className="flex-1"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Salvando...
                    </>
                  ) : (
                    "Salvar Configurações"
                  )}
                </Button>
                <Button
                  onClick={handleTestConnection}
                  disabled={isLoading}
                  variant="outline"
                  className="flex-1"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Testando...
                    </>
                  ) : (
                    "Testar Conexão"
                  )}
                </Button>
              </div>

              {saveStatus === "success" && (
                <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  Configurações salvas com sucesso!
                </div>
              )}

              {saveStatus === "error" && (
                <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                  <AlertCircle className="w-4 h-4" />
                  Erro ao salvar configurações
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Informações de Suporte</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                <strong>Subdomínio:</strong> A primeira parte da sua URL do Sienge (ex: minhaempresa em minhaempresa.sienge.com.br)
              </p>
              <p>
                <strong>Usuário:</strong> Seu email de login no Sienge
              </p>
              <p>
                <strong>Senha:</strong> Sua senha de acesso ao Sienge
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Settings;
