export type Role = "superadmin" | "owner" | "staff";
export type RestaurantRole = "owner" | "manager" | "waiter";

export type User = {
  id: number;
  username: string;
  email: string;
  role: Role;
};

export type MyRestaurant = {
  id: number;
  name: string;
  slug: string;
  logo: string | null;
  primary_color: string;
  is_active: boolean;
  role: RestaurantRole;
};

export type Restaurant = {
  id: number;
  user: User;
  name: string;
  slug: string;
  description: string | null;
  location: string | null;
  coordinates: Record<string, unknown>;
  logo: string | null;
  cover_image: string | null;
  primary_color: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Category = {
  id: number;
  restaurant: number;
  name: string;
  order: number;
  is_active: boolean;
};

export type Eat = {
  id: number;
  restaurant: number;
  category: number | null;
  name: string;
  description: string;
  price: string;
  image: string;
  model_url: string | null;
  model_url_usdz: string | null;
  model_status: string;
  model_progress: number | null;
  model_error: string | null;
  model_error_type: string | null;
  usdz_status: "" | "pending" | "ready" | "failed";
  usdz_error: string | null;
  usdz_error_type: string | null;
  created_at: string;
  updated_at: string;
};

export type Table = {
  id: number;
  restaurant: number;
  name: string;
  place: string;
  token: string;
  qr_code: string | null;
  menu_url: string;
  is_active: boolean;
};

export type RestaurantStaff = {
  id: number;
  restaurant: number;
  user: User;
  role: RestaurantRole;
  created_at: string;
};
