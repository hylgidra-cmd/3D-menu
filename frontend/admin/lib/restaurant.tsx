"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch } from "./api";
import type { MyRestaurant } from "./types";

type RestaurantContextValue = {
  restaurants: MyRestaurant[];
  current: MyRestaurant | null;
  setCurrentId: (id: number) => void;
  loading: boolean;
  refresh: () => Promise<void>;
};

const RestaurantContext = createContext<RestaurantContextValue | null>(null);

const CURRENT_KEY = "menu3d_current_restaurant";

export function RestaurantProvider({ children }: { children: ReactNode }) {
  const [restaurants, setRestaurants] = useState<MyRestaurant[]>([]);
  const [currentId, setCurrentIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<{ results: MyRestaurant[] }>("/api/restaurant/mine/");
      setRestaurants(data.results);
      const stored = Number(window.localStorage.getItem(CURRENT_KEY));
      const validStored = data.results.find((r) => r.id === stored);
      setCurrentIdState(validStored ? stored : data.results[0]?.id ?? null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch "my restaurants" once on mount
    refresh();
  }, []);

  const setCurrentId = (id: number) => {
    setCurrentIdState(id);
    window.localStorage.setItem(CURRENT_KEY, String(id));
  };

  const current = restaurants.find((r) => r.id === currentId) ?? null;

  return (
    <RestaurantContext.Provider value={{ restaurants, current, setCurrentId, loading, refresh }}>
      {children}
    </RestaurantContext.Provider>
  );
}

export function useRestaurant() {
  const ctx = useContext(RestaurantContext);
  if (!ctx) throw new Error("useRestaurant must be used within RestaurantProvider");
  return ctx;
}
