import { Bell, Sun, Settings, Menu, LayoutPanelLeft } from "lucide-react";

export function Header({ toggleSidebar }: { toggleSidebar: () => void }) {
  return (
    <header className="flex items-center justify-between p-4 border-b border-neutral-800">
      <div className="flex items-center gap-3 text-neutral-400">
        <button onClick={toggleSidebar} className="md:hidden hover:text-white">
          <Menu size={20} />
        </button>
        <button onClick={toggleSidebar} className="hidden md:block hover:text-white">
          <LayoutPanelLeft size={20} />
        </button>
      </div>
      
      <div className="flex items-center gap-4 text-neutral-400">
        <button className="hover:text-white transition-colors">
          <Bell size={18} />
        </button>
        <button className="hover:text-white transition-colors">
          <Sun size={18} />
        </button>
        <button className="hover:text-white transition-colors">
          <Settings size={18} />
        </button>
        <div className="w-8 h-8 rounded-full bg-neutral-800 border border-neutral-700 overflow-hidden flex items-center justify-center cursor-pointer">
          <span className="text-sm">T</span>
        </div>
      </div>
    </header>
  );
}
