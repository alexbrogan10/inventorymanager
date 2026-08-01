export interface ReorderSuggestion {
  product_id: number;
  sku: string;
  name: string;
  current_quantity: number;
  predicted_daily_demand: number;
  stock_depletion_date: string | null;
  days_until_depletion: number | null;
  reorder_quantity: number;
  confidence_score: number;
}

export interface OverstockWarning {
  product_id: number;
  sku: string;
  name: string;
  current_quantity: number;
  maximum_quantity: number | null;
  days_of_supply: number | null;
  reasons: string[];
}

export interface SlowMovingProduct {
  product_id: number;
  sku: string;
  name: string;
  current_quantity: number;
  quantity_sold_last_60_days: number;
  days_since_last_sale: number | null;
}

export type SeasonalPattern = 'weekend_spike' | 'weekday_light';

export interface SeasonalTrend {
  product_id: number;
  sku: string;
  name: string;
  pattern: SeasonalPattern;
  weekend_to_weekday_ratio: number;
}

export interface RecommendationsReport {
  model_trained: boolean;
  reorder_suggestions: ReorderSuggestion[];
  overstock_warnings: OverstockWarning[];
  slow_moving_products: SlowMovingProduct[];
  seasonal_trends: SeasonalTrend[];
}
