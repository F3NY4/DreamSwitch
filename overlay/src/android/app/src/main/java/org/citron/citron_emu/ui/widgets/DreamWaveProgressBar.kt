// SPDX-License-Identifier: GPL-3.0-or-later
// Draws a lightweight Material You wave only in app dialogs, never in the Vulkan game view.
package org.citron.citron_emu.ui.widgets

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.widget.ProgressBar
import androidx.core.graphics.ColorUtils
import com.google.android.material.color.MaterialColors
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.sin

class DreamWaveProgressBar @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = android.R.attr.progressBarStyleHorizontal
) : ProgressBar(context, attrs, defStyleAttr) {

    private val trackPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val wavePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val cursorPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val path = Path()
    private val bounds = RectF()
    private val density = resources.displayMetrics.density
    private var phase = 0f

    override fun onDraw(canvas: Canvas) {
        val left = paddingLeft.toFloat()
        val right = (width - paddingRight).toFloat()
        val centerY = height / 2f
        if (right <= left) return
        val strokeWidth = 5f * density
        val radius = strokeWidth / 2f
        val color = MaterialColors.getColor(
            this, androidx.appcompat.R.attr.colorPrimary
        )
        trackPaint.color = ColorUtils.setAlphaComponent(color, 58)
        trackPaint.strokeWidth = strokeWidth
        wavePaint.color = color
        wavePaint.strokeWidth = strokeWidth
        cursorPaint.color = color
        bounds.set(left, centerY - radius, right, centerY + radius)
        canvas.drawRoundRect(bounds, radius, radius, trackPaint)

        val range = max(1, max - min)
        val fraction = if (isIndeterminate) 0.32f else
            ((progress - min).toFloat() / range).coerceIn(0f, 1f)
        val end = left + (right - left) * fraction
        val amplitude = 5f * density
        val period = 32f * density
        val step = max(3f * density, 1f)
        path.reset()
        var x = left
        path.moveTo(left, centerY)
        while (x < end) {
            val waveY = centerY + amplitude * sin((x - left) / period * (2 * PI) + phase).toFloat()
            path.lineTo(x, waveY)
            x += step
        }
        path.lineTo(end, centerY + amplitude * sin((end - left) / period * (2 * PI) + phase).toFloat())
        canvas.drawPath(path, wavePaint)
        canvas.drawCircle(end, centerY, 8f * density, cursorPaint)

        if (isIndeterminate && isShown && isAttachedToWindow) {
            phase += 0.17f
            postInvalidateDelayed(48L)
        }
    }
}
