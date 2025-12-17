import { useState } from "react";
import { Upload, Loader2, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface UploadDialogProps {
  onUploadSuccess: () => void;
  className?: string;
}

export const UploadDialog = ({ onUploadSuccess, className }: UploadDialogProps) => {
  const [open, setOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { toast } = useToast();

  const handleUpload = async (file: File) => {
    if (file.size > 100 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Maximum file size is 100 MB",
        variant: "destructive",
      });
      return;
    }

    setIsUploading(true);

    try {
      await api.uploadFile(file);

      toast({
        title: "Success",
        description: `${file.name} uploaded successfully`,
      });

      setOpen(false);
      setSelectedFile(null);
      onUploadSuccess();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      toast({
        title: "Error",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="lg" className={cn("bg-primary hover:bg-primary/90 rounded-full px-6 transition-all duration-300 shadow-lg hover:shadow-xl", className)}>
          <Upload className="mr-2 h-5 w-5" />
          Upload New File
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-card/95 backdrop-blur-xl border-border/50 shadow-2xl duration-300 p-0 overflow-hidden gap-0">
        <DialogHeader className="p-6 pb-2">
          <DialogTitle className="text-xl font-light tracking-tight">Upload Document</DialogTitle>
          <DialogDescription className="text-muted-foreground/80">
            Drag & drop or select a file to start chatting.
          </DialogDescription>
        </DialogHeader>

        <div className="p-6 pt-2">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            className={cn(
              "relative group border border-dashed rounded-xl p-8 transition-all duration-300 ease-out",
              isDragging
                ? "border-primary bg-primary/5 scale-[0.99]"
                : "border-border/40 hover:border-primary/50 hover:bg-muted/30",
              isUploading && "pointer-events-none opacity-50",
              selectedFile ? "border-none bg-muted/30 p-4" : ""
            )}
          >
            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={handleFileSelect}
              disabled={isUploading}
              accept=".pdf,.docx,.txt,.md,.csv,.xlsx"
            />

            {selectedFile ? (
              <div className="flex items-center justify-between gap-4 animate-in fade-in zoom-in-95 duration-300">
                <div className="flex items-center gap-3 overflow-hidden">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Upload className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-sm font-medium text-foreground truncate">
                      {selectedFile.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                </div>

                {!isUploading && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setSelectedFile(null)}
                    className="h-8 w-8 rounded-full hover:bg-destructive/10 hover:text-destructive transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 text-center py-4">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                  <Upload className="h-6 w-6 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">
                    Drop your file here
                  </p>
                  <p className="text-xs text-muted-foreground/70">
                    PDF, DOCX, TXT, MD, CSV, XLSX up to 100MB
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => document.getElementById("file-upload")?.click()}
                  className="mt-2 rounded-full px-6 border-primary/20 hover:bg-primary/5 hover:text-primary hover:border-primary/50 transition-all duration-300"
                >
                  Browse Files
                </Button>
              </div>
            )}
          </div>

          {selectedFile && (
            <div className="mt-6 animate-in slide-in-from-bottom-2 duration-300">
              <Button
                onClick={() => selectedFile && handleUpload(selectedFile)}
                disabled={isUploading}
                className="w-full rounded-full h-11 font-medium shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  "Upload File"
                )}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
