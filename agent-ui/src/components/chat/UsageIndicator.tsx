/**
 * Personal usage readout for the chat sidebar.
 *
 * Shows today's and this month's token/request counts, the remaining monthly
 * allowance and the model the chat will use. Renders nothing while loading or
 * when usage is unavailable, so a usage hiccup never breaks the chat UI.
 */
import { useUsageMe } from "../../hooks/useUsage";
import { formatNumber, formatTokens, usagePercent } from "../../utils/format";
import ProgressBar from "../admin/ProgressBar";

export default function UsageIndicator() {
  const { data } = useUsageMe();

  if (!data) return null;

  const percent = usagePercent(data.tokens_this_month, data.monthly_token_limit);

  return (
    <div className="usage-indicator" aria-label="Usage">
      <div className="usage-indicator-head">
        <span className="usage-indicator-title">Usage</span>
        <span className="usage-indicator-model">
          {data.current_model ?? "default"}
        </span>
      </div>
      <div className="usage-indicator-row">
        <span>Today</span>
        <strong>
          {formatTokens(data.tokens_today)} tok · {formatNumber(data.requests_today)}{" "}
          req
        </strong>
      </div>
      <div className="usage-indicator-row">
        <span>This month</span>
        <strong>
          {formatTokens(data.tokens_this_month)} tok ·{" "}
          {formatNumber(data.requests_this_month)} req
        </strong>
      </div>
      <div className="usage-indicator-row">
        <span>Remaining</span>
        <strong>{formatTokens(data.tokens_remaining)} tok</strong>
      </div>
      <ProgressBar
        percent={percent}
        variant="mini"
        label="Monthly allowance used"
      />
      {!data.is_allowed && (
        <p className="usage-indicator-warn">Monthly allowance reached.</p>
      )}
    </div>
  );
}
