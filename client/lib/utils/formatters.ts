/**
 * Utility functions for formatting financial data
 */

// Helper function to format currency
export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '$0.00';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

// Helper function to format percentage (for IV - converts decimal to percentage)
export const formatPercentage = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  // Convert decimal to percentage (e.g., 0.143 -> 14.3%)
  return `${(value * 100).toFixed(1)}%`;
};

// Helper function to format ROI values (already in percentage form)
export const formatROI = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '0.0%';
  }
  // ROI values are already percentages (e.g., 85.2 -> 85.2%)
  return `${value.toFixed(1)}%`;
};

// Helper function to format volume
export const formatVolume = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '0';
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(0) + 'K';
  }
  return value.toString();
};