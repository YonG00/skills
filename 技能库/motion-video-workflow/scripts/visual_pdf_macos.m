// Native macOS PDF writer and round-trip renderer; no Python PDF dependencies.
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <CoreText/CoreText.h>
#import <ImageIO/ImageIO.h>
#import <math.h>

static CGContextRef ctx;
static CGRect bounds;
static CGColorRef ink, accent, muted, paper;

static void text(NSString *s, CGFloat x, CGFloat y, CGFloat size,
                 CGColorRef color, BOOL bold, BOOL right, CGFloat maxWidth) {
    CTLineRef line = NULL;
    CGFloat width = 0;
    do {
        if (line) CFRelease(line);
        CTFontRef font = CTFontCreateWithName((__bridge CFStringRef)
            (bold ? @"PingFangSC-Semibold" : @"PingFangSC-Regular"), size, NULL);
        NSDictionary *attrs = @{
            (__bridge id)kCTFontAttributeName: (__bridge id)font,
            (__bridge id)kCTForegroundColorAttributeName: (__bridge id)color};
        NSAttributedString *str = [[NSAttributedString alloc] initWithString:s attributes:attrs];
        line = CTLineCreateWithAttributedString((__bridge CFAttributedStringRef)str);
        width = CTLineGetTypographicBounds(line, NULL, NULL, NULL);
        CFRelease(font);
        if (width <= maxWidth || size <= 6) break;
        size -= .5;
    } while (YES);
    CGContextSetTextPosition(ctx, right ? x - width : x, y);
    CTLineDraw(line, ctx);
    CFRelease(line);
}

static NSString *stamp(double t) {
    int n = (int)t;
    return [NSString stringWithFormat:@"%02d:%02d:%02d", n / 3600, n / 60 % 60, n % 60];
}

static void beginPage(void) {
    CGPDFContextBeginPage(ctx, NULL);
    CGContextSetFillColorWithColor(ctx, paper);
    CGContextFillRect(ctx, bounds);
}

static void pageNumber(NSInteger n, NSInteger total) {
    text([NSString stringWithFormat:@"%ld / %ld", n, total],
         bounds.size.width - 24, 15, 10, muted, NO, YES, 90);
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) return 2;
        NSString *input = [NSString stringWithUTF8String:argv[1]];
        NSDictionary *job = [NSJSONSerialization JSONObjectWithData:
            [NSData dataWithContentsOfFile:input] options:0 error:NULL];
        if (!job) return 2;
        NSString *output = job[@"output"];
        NSArray *pages = job[@"pages"], *chapters = job[@"chapters"] ?: @[];
        CGFloat w = [job[@"page_width"] doubleValue], h = [job[@"page_height"] doubleValue];
        bounds = CGRectMake(0, 0, w, h);
        NSDictionary *info = @{(__bridge id)kCGPDFContextTitle: job[@"title"]};
        ctx = CGPDFContextCreateWithURL((__bridge CFURLRef)[NSURL fileURLWithPath:output],
                                       &bounds, (__bridge CFDictionaryRef)info);
        if (!ctx) return 3;
        ink = CGColorCreateGenericRGB(.098, .235, .282, 1);
        accent = CGColorCreateGenericRGB(.157, .478, .573, 1);
        muted = CGColorCreateGenericRGB(.42, .49, .5, 1);
        paper = CGColorCreateGenericRGB(.965, .961, .937, 1);
        NSInteger tocPages = (chapters.count + 9) / 10;
        NSInteger total = pages.count + 1 + tocPages;
        beginPage();
        text(job[@"title"], 40, h * .75, 40, ink, YES, NO, w - 80);
        text(@"画面合集", 42, h * .64, 28, accent, YES, NO, w - 84);
        text([NSString stringWithFormat:@"共 %lu 张画面，含完整状态与选定中间状态", pages.count],
             42, h * .46, 18, ink, NO, NO, w - 84);
        text(@"按讲解顺序编排；每页标注时间与主题。", 42, h * .37, 16, muted, NO, NO, w - 84);
        text([@"来源：" stringByAppendingString:job[@"source_label"]],
             42, 75, 11, muted, NO, NO, w - 84);
        pageNumber(1, total);
        CGPDFContextEndPage(ctx);

        for (NSInteger t = 0; t < tocPages; t++) {
            beginPage();
            text(@"目录", 40, h - 70, 30, ink, YES, NO, w - 80);
            for (NSInteger j = t * 10; j < MIN((t + 1) * 10, chapters.count); j++) {
                NSDictionary *ch = chapters[j];
                CGFloat y = h - 135 - (j % 10) * MIN(35, (h - 210) / 10);
                text(stamp([ch[@"start"] doubleValue]), 40, y, 15, accent, NO, NO, w * .20);
                text(ch[@"title"], w * .25, y, 17, ink, NO, NO, w * .62 - 30);
                text([ch[@"pdf_page"] stringValue], w - 40, y, 15, ink, NO, YES, 50);
            }
            text(@"时间对应所标明的成片或预览版本。", 40, 55, 11, muted, NO, NO, w - 80);
            pageNumber(t + 2, total);
            CGPDFContextEndPage(ctx);
        }

        for (NSInteger i = 0; i < pages.count; i++) {
            @autoreleasepool {
                NSDictionary *p = pages[i];
                CGImageSourceRef src = CGImageSourceCreateWithURL(
                    (__bridge CFURLRef)[NSURL fileURLWithPath:p[@"image"]], NULL);
                if (!src) return 4;
                CGImageRef image = CGImageSourceCreateImageAtIndex(src, 0, NULL);
                if (!image) { CFRelease(src); return 4; }
                double aspect = (double)CGImageGetWidth(image) / CGImageGetHeight(image);
                if (fabs(aspect - w / (h - 52)) > .01) return 4;
                beginPage();
                CGContextSetInterpolationQuality(ctx, kCGInterpolationHigh);
                CGContextDrawImage(ctx, CGRectMake(0, 52, w, h - 52), image);
                text(p[@"title"], 20, 32, 13, ink, YES, NO, w - 40);
                NSString *label = [NSString stringWithFormat:@"%@ - %@    截帧 %@    %@",
                    stamp([p[@"start"] doubleValue]), stamp([p[@"end"] doubleValue]),
                    stamp([p[@"time"] doubleValue]), p[@"state"]];
                text(label, 20, 12, 10, muted, NO, NO, w - 130);
                pageNumber(i + 2 + tocPages, total);
                CGPDFContextEndPage(ctx);
                CGImageRelease(image);
                CFRelease(src);
            }
        }
        CGPDFContextClose(ctx);
        CGContextRelease(ctx);
        CGPDFDocumentRef doc = CGPDFDocumentCreateWithURL(
            (__bridge CFURLRef)[NSURL fileURLWithPath:output]);
        if (!doc || CGPDFDocumentGetNumberOfPages(doc) != total) return 5;
        NSString *qa = job[@"qa_dir"];
        [[NSFileManager defaultManager] createDirectoryAtPath:qa
            withIntermediateDirectories:YES attributes:nil error:NULL];
        NSMutableArray *checked = [NSMutableArray array];
        for (NSNumber *number in job[@"check_pages"]) {
            NSInteger n = number.integerValue;
            if (n < 1 || n > total) return 5;
            CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
            CGContextRef bitmap = CGBitmapContextCreate(NULL, (size_t)w, (size_t)h, 8,
                (size_t)w * 4, cs, kCGImageAlphaNoneSkipLast);
            CGContextSetRGBFillColor(bitmap, 1, 1, 1, 1);
            CGContextFillRect(bitmap, bounds);
            CGContextDrawPDFPage(bitmap, CGPDFDocumentGetPage(doc, n));
            CGImageRef image = CGBitmapContextCreateImage(bitmap);
            NSString *file = [qa stringByAppendingPathComponent:
                [NSString stringWithFormat:@"page_%03ld.png", n]];
            CGImageDestinationRef dst = CGImageDestinationCreateWithURL(
                (__bridge CFURLRef)[NSURL fileURLWithPath:file], CFSTR("public.png"), 1, NULL);
            CGImageDestinationAddImage(dst, image, NULL);
            if (!CGImageDestinationFinalize(dst)) return 6;
            CFRelease(dst);
            CGImageRelease(image);
            CGContextRelease(bitmap);
            CGColorSpaceRelease(cs);
            [checked addObject:number];
        }
        NSDictionary *report = @{@"output": output, @"pages": @(total),
            @"frames": @(pages.count), @"rendered_checks": checked,
            @"page_size_points": @[@(w), @(h)], @"visual_review": @"pending"};
        [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:NULL]
            writeToFile:job[@"report"] atomically:YES];
        CFRelease(doc);
        CGColorRelease(ink); CGColorRelease(accent); CGColorRelease(muted); CGColorRelease(paper);
        printf("PDF_READY %ld pages\n", total);
    }
    return 0;
}
