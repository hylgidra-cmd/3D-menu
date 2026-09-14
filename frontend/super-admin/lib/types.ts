export type User = {
  id: number;
  username: string;
  email: string;
  role: string;
  is_superuser: boolean;
};

export type Restaurant = {
  id: number;
  user: User;
  name: string;
  slug: string;
  description: string | null;
  location: string | null;
  logo: string | null;
  primary_color: string;
  is_active: boolean;
  created_at: string;
};

export type PlatformStats = {
  restaurants: { total: number; active: number; inactive: number };
  users: number;
  tables: number;
  eats: { total: number; with_3d_model: number };
};
