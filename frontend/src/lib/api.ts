const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = {
  // Files
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/v1/files`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  },

  async getFiles(page = 1, pageSize = 12) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/files?page=${page}&page_size=${pageSize}`
    );

    if (!response.ok) {
      throw new Error("Failed to fetch files");
    }

    return response.json();
  },

  async deleteFile(fileId: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/files/${fileId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("Failed to delete file");
    }
  },

  async chat(fileId: string, message: string) {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/${fileId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Chat failed" }));
      throw new Error(error.detail || "Chat failed");
    }

    return response.json();
  },

  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: "GET",
      });
      return response.ok;
    } catch {
      return false;
    }
  },
};
