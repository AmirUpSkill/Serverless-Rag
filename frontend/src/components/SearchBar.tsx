import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export const SearchBar = ({ value, onChange }: SearchBarProps) => {
  return (
    <div className="relative w-full">
      <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Search for a file..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-12 h-12 bg-transparent border-none shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 rounded-full text-foreground placeholder:text-muted-foreground"
      />
    </div>
  );
};
