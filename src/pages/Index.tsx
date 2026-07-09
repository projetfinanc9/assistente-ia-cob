import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Bell, History, Settings, ArrowRight, BarChart3 } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto space-y-12">
          <div className="text-center space-y-4">
            <h1 className="text-5xl font-bold tracking-tight">
              Constru AI Connect
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Sistema de automação de cobranças e integração com Sienge
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card className="hover:shadow-lg transition cursor-pointer" onClick={() => navigate('/dashboard')}>
              <CardHeader>
                <BarChart3 className="w-8 h-8 text-primary mb-2" />
                <CardTitle>Dashboard</CardTitle>
                <CardDescription>
                  Visão geral do sistema de cobrança automática
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">
                  Acessar
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:shadow-lg transition cursor-pointer" onClick={() => navigate('/dashboard/history')}>
              <CardHeader>
                <History className="w-8 h-8 text-primary mb-2" />
                <CardTitle>Histórico</CardTitle>
                <CardDescription>
                  Consulte todos os envios de cobrança via WhatsApp
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">
                  Acessar
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:shadow-lg transition cursor-pointer" onClick={() => navigate('/dashboard/cobranca-config')}>
              <CardHeader>
                <Bell className="w-8 h-8 text-primary mb-2" />
                <CardTitle>Cobrança</CardTitle>
                <CardDescription>
                  Configure lembretes automáticos de cobrança
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">
                  Acessar
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>

            <Card className="hover:shadow-lg transition cursor-pointer" onClick={() => navigate('/dashboard/settings')}>
              <CardHeader>
                <Settings className="w-8 h-8 text-primary mb-2" />
                <CardTitle>Configurações</CardTitle>
                <CardDescription>
                  Configure suas credenciais do Sienge
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button className="w-full">
                  Acessar
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="text-center">
            <Button size="lg" onClick={() => navigate('/dashboard')}>
              Ir para o Dashboard
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
