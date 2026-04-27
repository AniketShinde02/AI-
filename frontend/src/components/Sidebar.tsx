import { 
  Search, 
  Home, 
  FileText, 
  Hash, 
  Bot, 
  PlusSquare, 
  LayoutGrid, 
  BookOpen, 
  HelpCircle, 
  ChevronDown, 
  PanelLeftClose, 
  Bell, 
  MoreHorizontal, 
  File,
  User
} from "lucide-react";

export function Sidebar({ isOpen, toggle }: { isOpen: boolean; toggle: () => void }) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 transform bg-[#000000] border-neutral-800 transition-all duration-300 ease-in-out md:relative flex flex-col overflow-hidden ${
        isOpen ? "translate-x-0 w-[260px] border-r" : "-translate-x-full w-[260px] md:translate-x-0 md:w-0 border-r-0"
      }`}
    >
      <div className="w-[260px] flex flex-col h-full shrink-0">
        {/* Top Profile Area */}
        <div className="flex items-center justify-between p-4">
          <button className="flex items-center gap-2 text-white hover:text-neutral-300 transition-colors">
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-blue-600 to-purple-600 flex items-center justify-center overflow-hidden">
              <User size={14} className="text-white" />
            </div>
            <span className="font-semibold text-sm">Gojo Sataro</span>
            <ChevronDown size={14} className="text-neutral-500" />
          </button>
          <div className="flex items-center gap-3 text-neutral-400">
            <button onClick={toggle} className="hover:text-white transition-colors">
              <PanelLeftClose size={18} />
            </button>
            <button className="hover:text-white transition-colors">
              <Bell size={18} />
            </button>
          </div>
        </div>

        {/* Main Navigation */}
        <div className="px-3 py-1 space-y-1">
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:text-white rounded-lg transition-colors">
            <Search size={18} /> Search
          </a>
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-white bg-neutral-800/80 rounded-lg transition-colors">
            <Home size={18} /> Home
          </a>
          <a href="#" className="flex items-center justify-between px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg transition-colors group">
            <div className="flex items-center gap-3">
              <FileText size={18} /> Pages
            </div>
            <MoreHorizontal size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>
        </div>

        {/* Scrollable Content */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          
          {/* Recents Section */}
          <div>
            <button className="flex items-center gap-2 px-3 text-[11px] font-semibold text-neutral-500 hover:text-neutral-300 transition-colors">
              Recents <ChevronDown size={12} />
            </button>
            <div className="mt-2 space-y-1">
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <Hash size={16} className="shrink-0" /> Simple Pipeline Build Guide
              </a>
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <File size={16} className="shrink-0" /> Untitled
              </a>
            </div>
          </div>

          {/* Agents Section */}
          <div>
            <button className="flex items-center gap-2 px-3 text-[11px] font-semibold text-neutral-500 hover:text-neutral-300 transition-colors">
              Agents <ChevronDown size={12} />
            </button>
            <div className="mt-2 space-y-1">
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <div className="w-5 h-5 shrink-0 rounded-full bg-gradient-to-tr from-orange-500 to-yellow-500 flex items-center justify-center text-[10px] text-white">AI</div>
                Lobe AI
              </a>
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <Bot size={16} className="shrink-0" /> Create a DevOps engineer who specia...
              </a>
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <PlusSquare size={16} className="shrink-0" /> Create Agent
              </a>
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <LayoutGrid size={16} className="shrink-0" /> Community
              </a>
              <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-900 hover:text-white rounded-lg truncate transition-colors">
                <BookOpen size={16} className="shrink-0" /> Resources
              </a>
            </div>
          </div>
        </nav>

        {/* Bottom Help Icon */}
        <div className="p-4 mt-auto shrink-0">
          <button className="text-neutral-500 hover:text-neutral-300 transition-colors">
            <HelpCircle size={18} />
          </button>
        </div>

      </div>
    </aside>
  );
}
