import AppBrand from "@/components/AppBrand";
import UserMenu from "@/components/UserMenu";

interface AppNavProps {
  brandTo?: string;
  hideUserMenu?: boolean;
}

export default function AppNav({ brandTo = "/", hideUserMenu = false }: AppNavProps) {
  return (
    <nav className="app-nav">
      <AppBrand to={brandTo} />
      {!hideUserMenu && (
        <div className="app-nav__end">
          <UserMenu />
        </div>
      )}
    </nav>
  );
}
