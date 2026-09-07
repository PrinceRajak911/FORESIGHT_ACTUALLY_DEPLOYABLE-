# Complexity & Design Explanations

## 1. Why not forecast each SKU with a separate model?
There are many SKUs and some have sparse histories. A global model lets products share
statistical structure while category/season features provide product context. Newer SKUs
remain a limitation and should be flagged as lower confidence in a production extension.

## 2. Why seasonal-naive?
It is the mandatory business baseline. A complex model is only justified if it beats a
simple seasonal reference under the same backtest.

## 3. Why WAPE instead of only MAPE?
Low-demand SKUs can make percentage errors explode. WAPE weights error by total demand and
is therefore more stable for the portfolio-level planning question.

## 4. Why rolling-origin backtesting?
A random split can expose the model to information from the future. Rolling-origin testing
simulates how the forecast would actually have been produced.

## 5. Why lag features?
Demand is autocorrelated. Recent weeks and seasonal lags provide direct information about
the next week's likely demand.

## 6. Why rolling statistics?
A mean captures level while standard deviation captures recent volatility. Both help the
risk layer interpret whether inventory coverage is comfortable.

## 7. Why risk is rule-based rather than another black-box model?
The brief requires transparent and explainable risk logic. Operations needs to know why a SKU
was labelled REORDER NOW or MARKDOWN / CLEAR.

## 8. Why lead-time demand?
A stockout decision is fundamentally about whether available inventory can cover expected
demand before replenishment arrives. Therefore the forecast is aggregated over the SKU's
lead time.

## 9. Why two separate risk dimensions?
A SKU can simultaneously have high demand risk and high inventory risk. Keeping stockout
and overstock scores separate makes the decisioning grid explainable.

## 10. Why rupee impact?
A list of 50 risky SKUs is less useful than a prioritised list showing which problems can
affect the most revenue or tie up the most capital.

## 11. Why API + dashboard?
The dashboard is for human planning. The API is for machine-to-machine consumption and
makes the scoring layer independently deployable.

## 12. What is deliberately not hidden?
The system reports the baseline and model WAPE, bias, selected model and limitations. A
poor backtest is a valid finding and should not be replaced with fabricated accuracy.
