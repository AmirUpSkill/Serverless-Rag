import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export const BackendStatus = () => {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkStatus = async () => {
      setIsChecking(true);
      const status = await api.healthCheck();
      setIsOnline(status);
      setIsChecking(false);
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Check every 30s

    return () => clearInterval(interval);
  }, []);

  if (isChecking && isOnline === null) {
    return null;
  }

  if (isOnline) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <CheckCircle2 className="h-3 w-3 text-green-500" />
        <span>Backend connected</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs text-destructive">
      <AlertCircle className="h-3 w-3" />
      <span>Backend offline</span>
    </div>
  );
};
