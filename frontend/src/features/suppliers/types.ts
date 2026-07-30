export interface Supplier {
  id: number;
  company_name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  lead_time_days: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupplierInput {
  company_name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  lead_time_days: number;
  notes: string | null;
}
