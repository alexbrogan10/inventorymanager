export interface TrainingSummary {
  trained_at: string;
  training_row_count: number;
  accuracy: number | null;
  feature_importance: Record<string, number>;
}

export interface ProductForecast {
  product_id: number;
  sku: string;
  name: string;
  current_quantity: number;
  predicted_daily_demand: number;
  stock_depletion_date: string | null;
  reorder_quantity: number;
  confidence_score: number;
  has_sufficient_history: boolean;
  model_accuracy: number | null;
  model_trained_at: string;
  feature_importance: Record<string, number>;
}
