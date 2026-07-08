import { Sparkles, Settings } from "lucide-react";
import { useNavigate } from "react-router-dom";

export const ChatHeader = () => {
  const navigate = useNavigate();

  return (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-3 flex-1">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <Sparkles className="w-6 h-6 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            constru.ia
          </h1>
          <p className="text-xs text-muted-foreground">
            Assistente de IA inteligente
          </p>
        </div>
      </div>
      <button
        onClick={() => navigate("/settings")}
        className="p-2 hover:bg-muted rounded-lg transition-colors"
        title="Configurações do Sienge"
      >
        <Settings className="w-5 h-5 text-muted-foreground" />
      </button>
    </div>
  );
};
