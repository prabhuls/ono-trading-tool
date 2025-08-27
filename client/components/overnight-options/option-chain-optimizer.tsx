import { Card } from '@/components/ui/card';
import { OptionChainData } from '@/types/overnight-options';
import { formatCurrency, formatPercentage, formatVolume } from '@/lib/mock-data/overnight-options';

interface OptionChainOptimizerProps {
  optionChain: OptionChainData[];
  expiration: string;
}

export function OptionChainOptimizer({ optionChain, expiration }: OptionChainOptimizerProps) {
  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold text-foreground mb-4">
        Option Chain Optimizer ({expiration})
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 text-muted-foreground font-medium">Strike</th>
              <th className="text-right py-2 text-muted-foreground font-medium">Bid</th>
              <th className="text-right py-2 text-muted-foreground font-medium">Ask</th>
              <th className="text-right py-2 text-muted-foreground font-medium">Volume</th>
              <th className="text-right py-2 text-muted-foreground font-medium">OI</th>
              <th className="text-right py-2 text-muted-foreground font-medium">IV</th>
            </tr>
          </thead>
          <tbody>
            {optionChain.map((option) => (
              <tr 
                key={option.strike}
                className={`
                  ${option.isHighlighted === 'buy' ? 'option-chain-row-buy' : ''}
                  ${option.isHighlighted === 'sell' ? 'option-chain-row-sell' : ''}
                  hover:bg-muted/50 transition-colors
                `}
              >
                <td className="py-2 font-medium text-foreground">
                  <div className="flex items-center gap-2">
                    {option.strike}
                    {option.isHighlighted === 'buy' && (
                      <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded-full font-medium">
                        BUY
                      </span>
                    )}
                    {option.isHighlighted === 'sell' && (
                      <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full font-medium">
                        SELL
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-2 text-right text-green-400">
                  {formatCurrency(option.bid)}
                </td>
                <td className="py-2 text-right text-red-400">
                  {formatCurrency(option.ask)}
                </td>
                <td className="py-2 text-right text-foreground">
                  {formatVolume(option.volume)}
                </td>
                <td className="py-2 text-right text-foreground">
                  {formatVolume(option.openInterest)}
                </td>
                <td className="py-2 text-right text-blue-400">
                  {formatPercentage(option.impliedVolatility)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Highlighted rows legend */}
      <div className="flex gap-4 mt-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-orange-500 opacity-20 border-l-2 border-orange-500"></div>
          <span className="text-muted-foreground">BUY 580</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 opacity-20 border-l-2 border-red-500"></div>
          <span className="text-muted-foreground">SELL 581</span>
        </div>
      </div>
    </Card>
  );
}