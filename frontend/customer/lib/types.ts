export type PublicRestaurant = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  location: string | null;
  logo: string | null;
  cover_image: string | null;
};

export type PublicEat = {
  id: number;
  name: string;
  description: string;
  price: string;
  image: string;
  category: number | null;
  model_url: string | null;
  model_url_usdz: string | null;
  model_status: string;
  model_progress: number | null;
  model_error: string | null;
};

export type PublicCategory = {
  id: number;
  name: string;
  order: number;
  eats: PublicEat[];
};

export type PublicTable = {
  id: number;
  name: string;
  place: string;
};

export type PublicMenu = {
  table: PublicTable;
  restaurant: PublicRestaurant;
  categories: PublicCategory[];
};

export type PaymentMethod = "cash" | "card" | "online";
