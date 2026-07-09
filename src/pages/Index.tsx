import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { MessageSquare, Zap, Shield, BarChart3, Bell } from "lucide-react";
import { Link } from "react-router-dom";

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-8 w-8 text-primary" />
            <h1 className="text-2xl font-bold">Constru AI Connect</h1>
          </div>
          <Link to="/dashboard">
            <Button>Acessar Dashboard</Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-24 text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-5xl font-bold mb-6">
            Automatize cobranças e integre com o Sienge
          </h2>
          <p className="text-xl text-muted-foreground mb-8">
            Envie lembretes automáticos via WhatsApp, acompanhe o histórico
            de cobranças e gerencie tudo em um único painel integrado ao Sienge.
          </p>
          <div className="flex gap-4 justify-center mb-12">
            <Link to="/dashboard">
              <Button size="lg" className="gap-2">
                <Zap className="h-5 w-5" />
                Começar Agora
              </Button>
            </Link>
            <Link to="/dashboard/cobranca-config">
              <Button size="lg" variant="outline">
                Configurar Cobrança
              </Button>
            </Link>
          </div>

          {/* Estatísticas */}
          <div className="grid md:grid-cols-3 gap-8 mt-16">
            <div>
              <div className="text-4xl font-bold text-primary mb-2">24/7</div>
              <p className="text-muted-foreground">Disponível sempre</p>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary mb-2">100%</div>
              <p className="text-muted-foreground">Automático</p>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary mb-2">Sienge</div>
              <p className="text-muted-foreground">Integração nativa</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-16">
        <h3 className="text-3xl font-bold text-center mb-12">Como Funciona</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardContent className="pt-6">
              <Shield className="h-12 w-12 text-primary mb-4" />
              <h4 className="font-bold mb-2">Conecte ao Sienge</h4>
              <p className="text-sm text-muted-foreground">
                Insira suas credenciais para integrar com sua conta Sienge
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <Bell className="h-12 w-12 text-primary mb-4" />
              <h4 className="font-bold mb-2">Configure Lembretes</h4>
              <p className="text-sm text-muted-foreground">
                Defina regras e mensagens de cobrança automática
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <MessageSquare className="h-12 w-12 text-primary mb-4" />
              <h4 className="font-bold mb-2">Envio via WhatsApp</h4>
              <p className="text-sm text-muted-foreground">
                Clientes recebem lembretes automáticos no WhatsApp
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <BarChart3 className="h-12 w-12 text-success mb-4" />
              <h4 className="font-bold mb-2">Acompanhe Resultados</h4>
              <p className="text-sm text-muted-foreground">
                Dashboard e histórico completo dos envios realizados
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Benefits */}
      <section className="bg-muted py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <h3 className="text-3xl font-bold mb-12 text-center">
              Por Que Constru AI Connect?
            </h3>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              <Card>
                <CardContent className="pt-6">
                  <h4 className="font-bold mb-3 flex items-center gap-2">
                    <Zap className="h-5 w-5 text-primary" />
                    Rápido
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Automação em tempo real. Reduza inadimplência sem esforço manual.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <h4 className="font-bold mb-3 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    Seguro
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Integração oficial com a API do Sienge. Dados protegidos.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <h4 className="font-bold mb-3 flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    Rastreável
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Histórico completo com métricas de sucesso em tempo real.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <h4 className="font-bold mb-3">💰 Econômico</h4>
                  <p className="text-sm text-muted-foreground">
                    Reduza custos com cobrança manual e aumente a eficiência.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <h4 className="font-bold mb-3">📱 WhatsApp Nativo</h4>
                  <p className="text-sm text-muted-foreground">
                    Comunicação direta pelo canal preferido dos seus clientes.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <h4 className="font-bold mb-3">⚙️ Fácil Configuração</h4>
                  <p className="text-sm text-muted-foreground">
                    Configure em minutos e comece a enviar cobranças hoje mesmo.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>© 2026 Constru AI Connect. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
