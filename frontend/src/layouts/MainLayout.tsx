import AssessmentIcon from '@mui/icons-material/Assessment';
import AssignmentIcon from '@mui/icons-material/Assignment';
import CategoryIcon from '@mui/icons-material/Category';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import DashboardIcon from '@mui/icons-material/Dashboard';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import LightModeIcon from '@mui/icons-material/LightMode';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsIcon from '@mui/icons-material/Notifications';
import PointOfSaleIcon from '@mui/icons-material/PointOfSale';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import {
  AppBar,
  Box,
  Button,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';

import { useAuth } from '../features/auth/useAuth';
import { NotificationBell } from '../features/notifications/NotificationBell';
import { NotificationToasts } from '../features/notifications/NotificationToasts';
import { useThemeMode } from '../theme/useThemeMode';

const DRAWER_WIDTH = 240;

interface NavItem {
  label: string;
  path: string;
  icon: ReactNode;
}

// One entry per top-level section. Populated as each feature milestone adds
// its own page (purchase orders, sales, ...).
const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { label: 'Products', path: '/products', icon: <Inventory2Icon /> },
  { label: 'Categories', path: '/categories', icon: <CategoryIcon /> },
  { label: 'Suppliers', path: '/suppliers', icon: <LocalShippingIcon /> },
  { label: 'Warehouses', path: '/warehouses', icon: <WarehouseIcon /> },
  { label: 'Purchase Orders', path: '/purchase-orders', icon: <AssignmentIcon /> },
  { label: 'Sales', path: '/sales', icon: <PointOfSaleIcon /> },
  { label: 'Reports', path: '/reports', icon: <AssessmentIcon /> },
  { label: 'Recommendations', path: '/recommendations', icon: <LightbulbIcon /> },
  { label: 'Notifications', path: '/notifications', icon: <NotificationsIcon /> },
];

function isNavItemActive(itemPath: string, currentPath: string): boolean {
  if (itemPath === '/') return currentPath === '/';
  return currentPath === itemPath || currentPath.startsWith(`${itemPath}/`);
}

export function MainLayout() {
  const { user, logout } = useAuth();
  const { mode, toggleMode } = useThemeMode();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  // Below `sm`, the permanent drawer would eat most of the viewport width -
  // it becomes a temporary, overlay drawer instead, opened via the hamburger
  // button and closed on navigation or backdrop click.
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  const drawerContent = (
    <List>
      {NAV_ITEMS.map((item) => (
        <ListItemButton
          key={item.path}
          component={Link}
          to={item.path}
          selected={isNavItemActive(item.path, location.pathname)}
          onClick={() => setMobileOpen(false)}
        >
          <ListItemIcon>{item.icon}</ListItemIcon>
          <ListItemText primary={item.label} />
        </ListItemButton>
      ))}
    </List>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
            {isMobile && (
              <IconButton
                color="inherit"
                aria-label="Open navigation menu"
                onClick={() => setMobileOpen(true)}
              >
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="h6" noWrap component="div">
              Inventory Manager
            </Typography>
          </Box>
          {user && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 2 } }}>
              <Tooltip title={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
                <IconButton color="inherit" aria-label="Toggle color mode" onClick={toggleMode}>
                  {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
                </IconButton>
              </Tooltip>
              <NotificationBell />
              <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' } }} noWrap>
                {user.full_name} · {user.role}
              </Typography>
              <Button color="inherit" onClick={handleLogout}>
                Logout
              </Button>
            </Box>
          )}
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
          }}
        >
          <Toolbar />
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
          }}
          open
        >
          <Toolbar />
          {drawerContent}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{ flexGrow: 1, p: { xs: 2, sm: 3 }, width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` } }}
      >
        <Toolbar />
        <Outlet />
      </Box>
      <NotificationToasts />
    </Box>
  );
}
