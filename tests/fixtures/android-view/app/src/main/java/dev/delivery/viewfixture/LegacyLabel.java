package dev.delivery.viewfixture;

import android.content.Context;
import androidx.appcompat.widget.AppCompatTextView;

public final class LegacyLabel extends AppCompatTextView {
    public LegacyLabel(Context context) {
        super(context);
        setText(R.string.legacy_label);
        setTextSize(18);
    }
}
