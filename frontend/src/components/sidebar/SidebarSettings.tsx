import { Monitor, Moon, Settings, Sun } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui"
import { useTheme } from "@/context/theme-provider"
import type { Theme } from "@/context/theme-provider"

export const SidebarSettings = () => {
  const { theme, setTheme } = useTheme()

  const themeOptions: { value: Theme; label: string; icon: React.ReactNode }[] =
    [
      { value: "light", label: "Light", icon: <Sun className="h-4 w-4" /> },
      { value: "dark", label: "Dark", icon: <Moon className="h-4 w-4" /> },
      { value: "system", label: "System", icon: <Monitor className="h-4 w-4" /> },
    ]

  return (
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            tooltip="Settings"
            className="group/button cursor-pointer"
          >
            <div className="flex items-center justify-center size-4">
              <Settings className="h-4 w-4" />
            </div>
            <span className="text-sm">Settings</span>
          </SidebarMenuButton>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="start" className="w-60">
          <DropdownMenuLabel>Appearance</DropdownMenuLabel>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <span className="flex items-center gap-2">
                {theme === "light" && <Sun className="h-4 w-4" />}
                {theme === "dark" && <Moon className="h-4 w-4" />}
                {theme === "system" && <Monitor className="h-4 w-4" />}
                <span>Toggle Theme</span>
              </span>
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              {themeOptions.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  onClick={() => setTheme(option.value)}
                  className="cursor-pointer flex items-center gap-2"
                >
                  {option.icon}
                  <span>{option.label}</span>
                  {theme === option.value && (
                    <div className="ml-auto size-2 rounded-full bg-current" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  )
}
