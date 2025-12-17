import { FileText, FileSpreadsheet, File } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatDate } from "@/lib/formatters";

interface FileData {
  id: string;
  name: string;
  type: string;
  size_bytes: number;
  summary: string | null;
  keywords: string[];
  created_at: string;
}

interface FileGridProps {
  files: FileData[];
  onFileClick: (fileId: string, fileName: string) => void;
}

const getFileIcon = (type: string) => {
  if (type === "pdf") return FileText;
  if (type === "xlsx" || type === "csv") return FileSpreadsheet;
  return File;
};

export const FileGrid = ({ files, onFileClick }: FileGridProps) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {files.map((file) => {
        const Icon = getFileIcon(file.type);
        
        return (
          <Card
            key={file.id}
            onClick={() => onFileClick(file.id, file.name)}
            className="group cursor-pointer bg-card hover:bg-secondary/50 border-border transition-all duration-200 hover:border-primary/50 overflow-hidden"
          >
            <div className="p-5 space-y-3">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10 flex-shrink-0">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                    {file.name}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(file.size_bytes)} • {formatDate(file.created_at)}
                  </p>
                </div>
              </div>

              {file.summary && (
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {file.summary}
                </p>
              )}

              {file.keywords && file.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {file.keywords.slice(0, 6).map((keyword, index) => (
                    <Badge
                      key={index}
                      variant="secondary"
                      className="text-xs bg-secondary text-secondary-foreground"
                    >
                      {keyword}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
};
