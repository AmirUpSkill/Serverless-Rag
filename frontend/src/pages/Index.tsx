import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { UploadDialog } from "@/components/UploadDialog";
import { FileGrid } from "@/components/FileGrid";
import { Pagination } from "@/components/Pagination";
import { Loader2, Database } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface FileData {
  id: string;
  name: string;
  type: string;
  size_bytes: number;
  summary: string | null;
  keywords: string[];
  created_at: string;
  updated_at: string;
}

interface PaginationData {
  page: number;
  page_size: number;
  total_pages: number;
  total_files: number;
}

const Index = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [files, setFiles] = useState<FileData[]>([]);
  const [filteredFiles, setFilteredFiles] = useState<FileData[]>([]);
  const [pagination, setPagination] = useState<PaginationData>({
    page: 1,
    page_size: 12,
    total_pages: 1,
    total_files: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchFiles = async (page = 1) => {
    setIsLoading(true);
    try {
      const data = await api.getFiles(page, 12);
      setFiles(data.files);
      setFilteredFiles(data.files);
      setPagination(data.pagination);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load files";
      toast({
        title: "Connection error",
        description: message,
        variant: "destructive",
      });
      console.error("Error fetching files:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === "") {
      setFilteredFiles(files);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = files.filter(
        (file) =>
          file.name.toLowerCase().includes(query) ||
          file.summary?.toLowerCase().includes(query) ||
          file.keywords?.some((keyword) =>
            keyword.toLowerCase().includes(query)
          )
      );
      setFilteredFiles(filtered);
    }
  }, [searchQuery, files]);

  const handleFileClick = (fileId: string, fileName: string) => {
    navigate(`/chat/${fileId}`, { state: { fileName } });
  };

  const handlePageChange = (page: number) => {
    fetchFiles(page);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="space-y-8">
          <div className="flex items-center w-full max-w-3xl mx-auto bg-card border border-border rounded-full shadow-sm px-2 py-1 focus-within:ring-2 focus-within:ring-ring transition-all">
            <div className="flex-1">
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
            </div>
            <div className="pl-2 border-l border-border">
              <UploadDialog onUploadSuccess={() => fetchFiles(pagination.page)} className="shadow-none" />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-12 w-12 text-primary animate-spin" />
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="text-center py-20 space-y-4">
              <Database className="h-16 w-16 mx-auto text-muted-foreground opacity-50" />
              <div>
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  {searchQuery ? "No files found" : "No documents yet"}
                </h3>
                <p className="text-muted-foreground">
                  {searchQuery
                    ? "Try a different search term"
                    : "Upload your first file to get started!"}
                </p>
              </div>
            </div>
          ) : (
            <>
              <FileGrid files={filteredFiles} onFileClick={handleFileClick} />

              {!searchQuery && pagination.total_pages > 1 && (
                <Pagination
                  currentPage={pagination.page}
                  totalPages={pagination.total_pages}
                  onPageChange={handlePageChange}
                  isLoading={isLoading}
                />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default Index;
