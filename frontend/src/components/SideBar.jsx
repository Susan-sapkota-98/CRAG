import { PanelLeftIcon, PenBoxIcon, PenSquare, Plus } from "lucide-react"
import { useState } from "react"

function SideBar() {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <div className="fixed lg:static inset-y-0 left-0 z-50 w-67.5 h-screen shrink-0 bg-[#0d0f14] border-r border-white/6 ">

      <div className="flex flex-col h-full">
        <div className="flex items-center gap-2.5 px-4 py-4 border-white/6">

          <div className="hidden lg:flex items-center justify-center w-7 h-7 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-colors duration-150 bg-transparent border-none cursor-pointer"
            onClick={() => setCollapsed(true)}>
            <PanelLeftIcon />
          </div>

          <span className="text-[16px] font-semibold text-slate-100 tracking-tight flex-1">Thinkora</span>

          <span className="text-[10px] font-medium text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full tracking-wide">
            free
          </span>

          <button className="flex items-center justify-center w-7 h-7 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-colors duration-150 bg-transparent border-none cursor-pointer">
            <PenSquare size={14} />
          </button>


        </div>

        <div className="px-6  pt-4 pb-1">
          <button className=" px-2 w-full flex items-center gap-2 text-sm font-medium text-white bg-linear-to-br from-indigo-500 to-violet-700 rounded-xl py-2.5 border-none cursor-pointer hover:opacity-90 transaction-opacity duration-150">
            <Plus />
            New Chat
          </button>
        </div>

      </div>

    </div>
  )
}

export default SideBar