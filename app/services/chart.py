"""
Chart Service
Generates matplotlib charts for financial metrics
"""
import io
import logging
from typing import List
import matplotlib.pyplot as plt
import matplotlib
from app.schemas.analysis import CompanyMetric

# Use non-interactive backend
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

class ChartService:
    def generate_comparison_chart(
        self, 
        metrics_list: List[CompanyMetric],
        title: str = "Financial Comparison"
    ) -> bytes:
        """
        生成比較圖表
        
        Args:
            metrics_list: List of company metrics to plot
            title: Chart title
            
        Returns:
            PNG image bytes
        """
        plt.figure(figsize=(10, 6))
        
        # Plot each company
        for metric in metrics_list:
            # Sort data by time
            sorted_data = sorted(
                metric.data, 
                key=lambda x: (x.year, x.quarter)
            )
            
            x_labels = [f"{d.year}Q{d.quarter}" for d in sorted_data]
            y_values = [d.value for d in sorted_data]
            
            label = f"{metric.stock_id} {metric.metric_name}"
            if metric.company_name:
                label = f"{metric.stock_id} {metric.company_name}"
                
            plt.plot(x_labels, y_values, marker='o', label=label)

        plt.title(title)
        plt.xlabel("Quarter")
        plt.ylabel(metrics_list[0].metric_name if metrics_list else "Value")
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # Rotate x labels if many points
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close()
        
        buf.seek(0)
        return buf.getvalue()


# Singleton
_chart_service = None

def get_chart_service() -> ChartService:
    global _chart_service
    if _chart_service is None:
        _chart_service = ChartService()
    return _chart_service
